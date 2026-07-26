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

## Three bugs I only found by running it

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

None of the three are things I'd have predicted from reading the docs.

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
