---
title: "Slinky GitOps"
date: 2026-07-26
description: "Slurm on Kubernetes from nothing in one command — and the auth-key rotation nobody wants to test in production."
summary: "Slurm on Kubernetes from nothing in one command — and the auth-key rotation nobody wants to test in production."
tags: [slurm, kubernetes, slinky, helm, gitops]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/slinky-gitops"
weight: 2
ShowToc: false
---

**[github.com/Zhanyl-tech/slinky-gitops](https://github.com/Zhanyl-tech/slinky-gitops)** · MIT

```
make up
```

Three-node KinD cluster → cert-manager → Slinky operator → a Slurm cluster that
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

## Every MUNGE rotation guide describes a component that isn't installed

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
a shared key file. Slinky uses it. **MUNGE is not installed.**

So the hazard is unchanged — one shared secret, every daemon, no atomic
switchover — but the mechanism, the secret names, and the restart procedure in
every tutorial are wrong. The secrets are `slurm-auth-slurm` (`slurm.key`) and
`slurm-auth-jwt` (`jwt.key`).

Building from the brief instead of from the running cluster would have produced
a polished tool for a component that isn't there.

## Rotation, done carefully

There's no atomic moment. Between writing the new key and every daemon reloading
it, some hold the old key and some the new, and those two sets cannot
authenticate to each other. `auth/slurm` has no key versioning and no grace
period.

So: refuse to start unless the cluster is healthy and actually on `auth/slurm`;
drain first, because running jobs are what a failed rotation destroys; keep the
previous key so rollback is one command; verify end to end with a call that
round-trips through the auth plugin; roll back automatically if that fails.

## Four bugs I only found by running it

**The auth secrets are immutable.** `kubectl patch` is rejected outright —
`field is immutable when immutable is set`. The only path is delete-and-recreate,
carrying the labels so the operator and Helm still recognise it.

**The first version failed exactly there and left the cluster drained.** Which
is worse than not having rotated. Failure now resumes nodes on every exit path.

**Delete-and-recreate silently drops `immutable: true`.** You get a working,
*mutable* secret. Everything keeps running, so nothing tells you the posture
just weakened. That's the one I'd have shipped without noticing — it's invisible
unless you go looking. The flag is now captured before the delete and restored
after, verified by rotating twice and re-checking.

**The verification step verified nothing.** This is the one worth keeping.

CI failed with the rotation printing a green tick on every step, then
`Rotation complete`, and then:

```
srun: Required node not available (down, drained or reserved)
```

Rotation can only break one thing — the trust between `slurmctld` and `slurmd`,
because that's what the rotated key authenticates. My check ran `sinfo` *inside
the controller pod* and looked at the exit code, which never touches that
relationship: `slurmctld` answers a local client whether or not a single compute
node ever came back. It would have passed against a cluster with zero nodes.

Pulling that thread found four defects, all the same bug — **a check that can't
fail:**

| Check | Why it passed anyway |
| --- | --- |
| `sinfo` exits 0 | Never leaves the controller pod |
| No `*` on any node state | Raced the restart; passed 130 ms after it |
| `grep -E '^(idle\|mix\|alloc)'` | Also matches `idle*` — a node that can't be reached, i.e. the failure itself |
| Wait for replacement pods | No success flag, so a timeout fell through to a green tick |

And one defect in the deployment rather than my script:

```
$ kubectl get pod slurm-worker-slinky-0 -o jsonpath='{.metadata.ownerReferences[*].kind}'
NodeSet
```

`kubectl rollout restart` only understands built-in workload kinds. `NodeSet` is
a CRD, so the command I trusted to cycle every daemon silently skipped the one
on the far side of the boundary I was rotating. The controller took the new key
in seconds; slurmd kept the old one.

## The part I couldn't fix

With all of that corrected, the rotation still fails — and now says so. On a
clean cluster, with the Secret holding a new key and stable for five minutes, a
slurmd pod deleted and recreated from scratch came up mounting the **previous**
key:

```
secret                        c5016281…
slurmd pod created 02:28:25   8cbda076…   ← pre-rotation key
slurmctld                     c5016281…   ← correct
```

Slinky ships the auth Secret `immutable: true`, so its data can't be patched and
delete-and-recreate is the only route — after which the node's kubelet keeps
serving its cached copy to *newly created* pods. What I ruled out, because being
precise about the boundary of what I know is the whole point:

- **Not the operator rewriting it** — one value, `resourceVersion` unchanged, for 90s.
- **Not immutability** — recreating the replacement as mutable behaves identically.
- **Not universal** — the same delete-and-recreate against a Secret that node had never cached propagates instantly. That control test made me dismiss the whole thing too early, until I realised it didn't reproduce the one condition that matters: a pod holding the Secret continuously across the swap.

I can reproduce it on demand and I can't attribute it to a specific kubelet code
path, so the repo doesn't claim one.

What the tool does about it is the actual deliverable: it hashes `slurm.key`
inside every slurmd pod, compares it to the Secret, and **rolls back and exits
non-zero on mismatch**. CI asserts that safety property rather than a success it
can't have — `make rotate` must fail, and the cluster must still run a job
afterwards.

The general form is worth more than any single bug: **a check that doesn't cross
the boundary you might have broken will pass no matter what you broke.** Green
ticks on a dead cluster are worse than a red one, because they stop you looking.

None of this is something I'd have predicted from reading the docs.

## Honest scope

The repo says this plainly and so should this page: **ArgoCD is not wired up
yet**, so "GitOps" in the name is currently aspirational. What exists is
declarative and reproducible, applied by Make rather than reconciled by a
controller. One nodeset, one replica — enough to prove registration and job
execution; autoscaling profiles and multi-nodeset scheduling aren't built. No
login node; jobs are submitted from the controller pod.

Also worth noting for anyone mid-upgrade: **Slinky v1.2 ships Slurm 26.05**. The
Kubernetes path is already a release ahead of the 25.11 most on-prem clusters
are planning for.
