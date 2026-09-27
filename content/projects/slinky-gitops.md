---
title: "Slinky GitOps"
date: 2026-07-26
lastmod: 2026-09-26
description: "Slurm 26.05 on Kubernetes (kind) with SchedMD's Slinky operator in one command, and an auth-key rotation that measures whether it worked. On Slinky v1.2 it does not, and the script rolls back."
summary: "Slurm 26.05 on Kubernetes (kind) with the Slinky operator, and an auth-key rotation that measures whether it worked. On Slinky v1.2 it does not, and the script rolls back."
tags: [slurm, kubernetes, slinky, slurm-operator, helm]
status: "Bring-up works · rotation blocked, fails safe · Argo CD not wired"
stage: "partial"
repo: "https://github.com/Zhanyl-tech/slinky-gitops"
weight: 3
ShowToc: true
---

**[github.com/Zhanyl-tech/slinky-gitops](https://github.com/Zhanyl-tech/slinky-gitops)** · Shell, Python · MIT

<p class="project-status"><span class="status status-partial">partial</span>
Built: a kind cluster running Slurm 26.05 under the Slinky operator v1.2 that
registers a node and runs jobs, and a rotation script with offline tests. The
rotation itself <strong>does not succeed on Slinky v1.2</strong>: it detects
that and rolls back. There is no GitOps controller yet; "GitOps" is the goal,
not the state. The September 2026 changes (version pinning, stricter checks)
are covered by the offline tests and have not been re-run on a cluster.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26. Merge or push it before publishing. -->

```
make up
```

Three-node kind cluster → cert-manager → Slinky operator → a Slurm cluster that
registers a compute node and runs jobs. Verified end to end on Apple Silicon:
**the Slinky images are multi-arch**, which is not obvious and is the first
thing that stops most people.

```
$ make job
slinky-0

$ make status
all*  up  infinite  1  idle  slinky-0
NodeName=slinky-0 Arch=aarch64 State=IDLE+DYNAMIC_NORM
```

Versions are pinned in the Makefile: Slinky operator and charts 1.2.0, the
`kindest/node:v1.32.2` image by digest, cert-manager 1.20.4. **Slinky v1.2
ships Slurm 26.05**, a release ahead of the 25.11 many on-prem clusters are
planning for.

## On Slinky the shared secret is auth/slurm, not MUNGE

I set out to build a MUNGE key-rotation sidecar. Then I deployed the thing and
checked:

```
$ scontrol show config | grep -i auth
AuthType     = auth/slurm
CredType     = cred/slurm
AuthAltTypes = auth/jwt

$ pgrep munged
(nothing)
```

Slurm 23.11 introduced `auth/slurm`, an internal plugin that replaces MUNGE with
a shared key. Slinky ships it as two Secrets, `slurm-auth-slurm` (`slurm.key`)
and `slurm-auth-jwt` (`jwt.key`). The hazard is the familiar one — one shared
secret, every daemon — but there is no `munged` to restart.

Slurm itself can rotate `auth/slurm` keys without a full restart, through a
`slurm.jwks` file that holds several keys at once
([authentication docs](https://slurm.schedmd.com/authentication.html)). Slinky
v1.2 has no way to ship that file: its operator projects exactly one key into
every Slurm pod, and its admission webhook rejects any change to the key
reference after deployment (both read in the v1.2.0 source; details in the
README). With one key there is no overlap window, so the rotation has to be the
careful single-key kind.

![Rotating auth/slurm on Slinky: the Secret holds the new key, slurmctld adopts it, and a new slurmd pod comes up with the previous key (suspected, not yet confirmed: the kubelet's cached copy), so the controller-to-slurmd trust boundary breaks and the rotation rolls back](/images/diagrams/slinky-auth-rotation.svg)

## What the rotation script does

1. Refuses to start unless the cluster is healthy and really on `auth/slurm`,
   and treats a health query that errors as a refusal, not a pass.
2. Drains only the nodes in service, with a reason unique to the run.
3. Backs up the current key and stages the new one before the live Secret is
   deleted, so both keys exist in the cluster at every moment. No key ever
   appears on a command line.
4. Restarts every daemon that holds the key, including slurmd, which
   `kubectl rollout restart` does not reach (below).
5. **Verifies by measurement:** hashes `slurm.key` on disk inside every slurmd
   pod and inside slurmctld and compares the hashes to the Secret, then
   requires every drained node to become schedulable again.
6. Rolls back automatically on any failure, and verifies the rollback the same
   way.

Exit codes are the interface: 0 rotated and verified, 1 refused, 3 the new key
did not take and the previous key was restored and verified, 4 needs a human.
On Slinky v1.2 it exits 3.

## Four bugs I only found by running it

**The auth Secrets are immutable.** `kubectl patch` is rejected outright; the
only path is delete-and-recreate, carrying the labels and annotations that Helm
records ownership in. The first version failed exactly there and left the
cluster drained, which is why an exit trap now restores a working cluster on
every exit path.

**Recreating an immutable Secret silently drops `immutable: true`.** Everything
keeps running, so nothing tells you the posture just weakened. The flag is
carried over, and CI compares the Secret's hash, flag, labels and annotations
before and after every rotation and rollback.

**The verification step verified nothing.** CI failed with every step printing
a green tick, then `Rotation complete`, and then:

```
srun: Required node not available (down, drained or reserved)
```

Rotation can only break one thing, the trust between `slurmctld` and `slurmd`,
because that is what the key authenticates. Every early check missed it the
same way — **a check that cannot fail**:

| Check | Why it passed anyway |
| --- | --- |
| `sinfo` exits 0 | Never leaves the controller pod |
| No `*` on any node state | Raced the restart; passed 130 ms after it |
| `grep -E '^(idle\|mix\|alloc)'` | Also matches `idle*` — a node that can't be reached, i.e. the failure itself |
| Wait for replacement pods | No success flag, so a timeout fell through to a green tick |

**`kubectl rollout restart` skipped slurmd.**

```
$ kubectl get pod slurm-worker-slinky-0 -o jsonpath='{.metadata.ownerReferences[*].kind}'
NodeSet
```

`rollout restart` only understands built-in workload kinds. `NodeSet` is a
custom resource, so the command I trusted to cycle every daemon silently
skipped the one on the far side of the boundary being rotated. The controller
took the new key in seconds; slurmd kept the old one.

## The part that still fails: the key does not propagate

With all of that fixed, the rotation still fails, and now says so. On a clean
kind cluster, with the Secret holding a new key and stable for five minutes, a
slurmd pod deleted and recreated from scratch came up mounting the **previous**
key:

```
secret                        c5016281…
slurmd pod created 02:28:25   8cbda076…   ← pre-rotation key
slurmctld                     c5016281…   ← correct
```

Established so far: it is not the operator rewriting the Secret (one value,
`resourceVersion` unchanged, for 90 s), it is not the replacement Secret's own
immutability (recreating it as mutable behaves the same), and it is not
universal (the same delete-and-recreate against a Secret the node had never
cached propagates at once).

**Current explanation — a hypothesis from reading the code, not yet reproduced
in isolation.** The kubelet's default Secret strategy is a watch-based cache
keyed by namespace and name. In
[`pkg/kubelet/util/manager/watch_based_manager.go`](https://github.com/kubernetes/kubernetes/blob/v1.32.2/pkg/kubelet/util/manager/watch_based_manager.go)
(v1.32.2), once the cached object is immutable the watch for it is stopped, and
the item is dropped only when no pod on that node references the name any more.
So once a node has cached `slurm-auth-slurm` as immutable, new pods there get
the cached bytes for as long as any pod on the node still mounts that name. The
Kubernetes documentation says as much in passing: "The kubelet does not need
to maintain a watch on any Secrets that are marked as immutable", and after
deleting one, "Existing Pods maintain a mount point to the deleted Secret - it
is recommended to recreate these pods"
([Secrets](https://kubernetes.io/docs/concepts/configuration/secret/#secret-immutable)).
That predicts all three observations above. The README lists four experiments
that would confirm or kill it; none has been run yet. An upstream issue for
SlinkyProject/slurm-operator is drafted in the repository and has not been
filed.

What the script does about it is the deliverable: it detects the mismatch,
rolls back, verifies the rollback, and exits 3. CI asserts that safety property
rather than a success it cannot have — the rotation must exit 3 for the
documented reason, the Secrets must be exactly as they were, and the cluster
must still run a job afterwards.

The general form is worth more than any single bug: **a check that doesn't
cross the boundary you might have broken will pass no matter what you broke.**

## Honest scope

- **kind only.** The Helm values and the rotation apply to any Kubernetes; the
  bring-up path is local.
- **One NodeSet, one replica.** Enough to prove registration and job
  execution. No login node (`LoginSet`), no accounting (slurmdbd), no GPU GRES
  classes, no topology configuration.
- **No GitOps controller.** Applied by Make, not reconciled by Argo CD. Wiring
  Argo CD to these values as they are would not work: the chart generates both
  keys with Helm `lookup` plus a random value, and Argo CD renders charts with
  `helm template`, where `lookup` finds nothing, so every sync would see new
  keys. The keys have to come from outside the chart first.
- **Not re-run on a cluster since the September 2026 changes.**
