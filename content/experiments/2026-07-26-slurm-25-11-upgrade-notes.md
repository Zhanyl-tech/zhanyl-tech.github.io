---
title: "I Was Planning a Slurm 25.11 Upgrade. Then 26.05 Shipped."
date: 2026-07-26
description: "Three versions, two config renames that break on restart, and one cgroup change that quietly breaks every job-attribution tool you own."
tags: [slurm, hpc, upgrade, prometheus, cluster-operations]
summary: "Three versions, two config renames that break on restart, and one cgroup change that quietly breaks every job-attribution tool you own."
ShowToc: false
draft: false
---

I had a plan. Move a 250-node cluster from 25.05 to 25.11, write it up, ship it.

Then I checked the release list and found 26.05 had gone out on July 14, along
with 25.11.7. Twelve days ago. And 26.05 upgrades **directly** from 25.05 —
which means the version I was carefully planning to land on is not the only
option, and possibly not the right one.

So this is the comparison I actually needed: three versions, what breaks between
them, and which one a cluster with one head node and 250 compute nodes should
be aiming at.

## The short version

| | 25.05 | 25.11 | 26.05 |
| --- | --- | --- | --- |
| Status | current on my cluster | stable, .7 out | **latest**, .2 out |
| Direct upgrade from | — | 25.05, 24.11, 24.05 | 25.11, 25.05, 24.11 |
| Config renames | — | `JobContainerType` | `ExclusiveUser`, `ExclusiveTopo` |
| Prometheus | none | basic openmetrics | **+ GPU allocation stats** |
| cgroup layout | JobId | JobId | **SLUID** |
| REST | v0.0.41 deprecated | v0.0.41 → removed | v0.0.42 deprecated |

Both 25.11 and 26.05 are reachable in one hop from 25.05. That is the whole
decision: one change window or two.

## The renames that fail on restart

Two of them, one per version, and both are the same class of problem — your
config parses fine today and does not parse after the daemon restarts.

**25.11 renamed `JobContainerType` to `NamespaceType`.** The `job_container`
plugin interface became `namespace`, with a new `namespace/linux` plugin that
handles filesystem, PID, and user namespaces. If you do per-job private `/tmp` —
and if you have users, you do — this line is in your config.

**26.05 collapsed `ExclusiveUser` and `ExclusiveTopo`** into a single
`Exclusive=[NO|NODE|USER|TOPO]`.

Neither is hard. Both are a `grep`:

```bash
grep -rnE 'JobContainerType|ExclusiveUser|ExclusiveTopo' /etc/slurm/
```

The reason to care is *when* you find out. A config-parse failure surfaces when
`slurmctld` restarts, which on a planned upgrade is the exact moment you have a
change window open, 250 nodes drained, and a room full of people waiting. Find
it on a Tuesday instead.

## The one that will break your tooling

This is the change I would have missed, and it is the expensive one:

> cgroup/v2 directory structures are now keyed off of SLUID and not the JobId.

Read that again if you own any monitoring that walks cgroups.

The standard way to attribute a process — or a GPU, or an InfiniBand counter —
back to a Slurm job is to walk `/sys/fs/cgroup/.../slurm/uid_*/job_*/` and match
PIDs. Every job-aware exporter I know of does some version of this. In 26.05 that
path is keyed by SLUID, not JobId, so anything parsing a job ID out of the
directory name gets a value that is not a job ID.

It will not error. It will return the wrong number, or nothing, and your
dashboards will go quietly flat.

I have a direct stake in this one: I have been building a GPU-waste reaper whose
next milestone is exactly this cgroup walk, and the note above means the
implementation I sketched is already obsolete for anyone on 26.05. Better to
learn that from a release note than from a silent regression six months in.

The API changed underneath it too — `slurm_step_id_t` replaces bare `job_id` in
calls, so the API can be queried by SLUID. There is a `SLURM_BACKWARD_COMPAT`
define if you compile against the C API, which is a kindness, but it is a
deprecation runway rather than a permanent fix.

## The good part

26.05 expands the openmetrics endpoints with **GPU allocation statistics**.

25.11 added native Prometheus export from `slurmctld` — queue depth, job states,
node states, scheduler cycle timing. Useful, and it kills the fragile
shell-out-to-`sinfo`-and-parse sidecar that a lot of sites still run.

26.05 adds GPU allocation to that. Which matters more than it sounds, because
"how many GPUs are allocated" and "how many GPUs are doing work" are different
questions and the gap between them is where cluster money goes. Native export
answers the first for free. The second still needs someone reading NVML, but
having the denominator without deploying anything is a real improvement.

Also in 26.05: `srun --async`, which queues step processes through stepmgr
instead of requiring you to keep hundreds of backgrounded `srun` processes
alive. If you have ever watched a workflow tool fork a thousand `srun`s and then
watched the login node fall over, this is for you. Plus dynamic memory resizing
— a running job can hand memory back via `scontrol update`, with
`sbatch --mem-update=<margin>@<delay>` to automate it — and new `topology/ring`
and `topology/torus3d` plugins.

25.11's headline was **expedited requeue**: `--requeue=expedite` puts a job that
died to node failure straight back at the top of the queue, and holds its
previous nodes so nothing else grabs them. For a training run that fell over at
hour 40, that is the difference between restarting now and restarting behind
everything that queued up while it ran.

One caution on it. Expedited requeue also triggers when the batch script exits
non-zero *and* an Epilog fails. But a failing Epilog is frequently how you learn
a node is sick. Wire "Epilog failed" to "requeue at top priority and hold those
nodes" and a genuinely bad node can pin an expedited job in a loop. If you turn
this on, your Epilog health check needs to drain decisively, not just exit
non-zero.

## Which one

For this cluster, 26.05.

The upgrade path is the same length either way — one hop from 25.05 — and taking
25.11 means doing the whole exercise again in a few months to get to a release
that is already out. The 250-node `slurmd` roll is the expensive part, and it
costs the same whichever target you pick. Paying it twice for no reason is the
easiest mistake to avoid here.

The argument against is real, though: 25.11 has had eight point releases and
26.05 has had two. If your cluster is the one people ship from and you cannot
tolerate being an early adopter of a `.2`, take 25.11 now and 26.05 in six
months. That is a legitimate risk call, not a cop-out — it just costs you two
change windows.

What I would not do is default to 25.11 because it was the plan before I looked.

## Order of operations

Nothing exotic, and unchanged across both versions:

1. `grep` the config for `JobContainerType`, `ExclusiveUser`, `ExclusiveTopo`.
2. Audit anything talking REST for a pinned API version. v0.0.41 is gone in
   26.05; v0.0.42 is deprecated there and goes in 26.11.
3. **Audit anything walking cgroups.** This is the new one, and it is the one
   that fails silently.
4. Back up `slurmdbd`. The database migration is the step with no easy undo, and
   it is the step people skip because it has always worked before.
5. `slurmdbd` → verify → `slurmctld` → verify.
6. Roll `slurmd` in batches, draining ahead of each. Never a compute node ahead
   of the controller.
7. New features *after* the version move is stable. Expedited requeue and the
   GPU metrics endpoints are not part of the upgrade; they are the next change.

I am writing that up properly — node batching, rollback triggers, the actual
runbook — as its own repo.

## What this is and isn't

This is release notes plus a decision, not a war story. I have not run 25.05 →
26.05 on 250 nodes yet. When I do, the useful post is the delta between this
plan and what actually happened, because that gap is where the real content
always is.

If you have already made either hop, I would like to know what bit you —
particularly whether the cgroup change broke anything you did not expect.

**Sources:** [Slurm 26.05 release notes](https://slurm.schedmd.com/release_notes.html) ·
[26.05 RELEASE_NOTES.md](https://github.com/SchedMD/slurm/blob/slurm-26.05/RELEASE_NOTES.md) ·
[25.11 RELEASE_NOTES.md](https://github.com/SchedMD/slurm/blob/slurm-25.11/RELEASE_NOTES.md) ·
[26.05.2 / 25.11.7 announcement](https://lists.schedmd.com/mailman3/hyperkitty/list/slurm-users@lists.schedmd.com/message/RBO6LEZNM754W22473U3XW643OEPPVS6/) ·
[Upgrade guide](https://slurm.schedmd.com/upgrades.html)
