---
title: "I Was Planning a Slurm 25.11 Upgrade. Then 26.05 Shipped."
date: 2026-07-26
lastmod: 2026-09-27
description: "Three versions, two renamed config options that now log deprecation warnings, and one cgroup change that quietly breaks job-attribution tools. Corrected September 2026 against Slurm's source."
tags: [slurm, hpc, upgrade, prometheus, cluster-operations]
summary: "Three versions, two renamed config options that now log deprecation warnings, and one cgroup change that quietly breaks job-attribution tools. Corrected September 2026."
ShowToc: false
draft: false
---

> **Update and correction, 26 September 2026.**
>
> - **Security releases.** On 2 September 2026 SchedMD published Slurm
>   **26.05.4**, **25.11.8** and **25.05.9**, fixing CVE-2026-65107, -65108,
>   -65109, -65138, -65139, -65140 and -65165 (all three), plus CVE-2026-65168
>   (25.11.8 and 25.05.9) ([26.05.4](https://github.com/SchedMD/slurm/releases/tag/slurm-26-05-4-1),
>   [25.11.8](https://github.com/SchedMD/slurm/releases/tag/slurm-25-11-8-1),
>   [25.05.9](https://github.com/SchedMD/slurm/releases/tag/slurm-25-05-9-1)).
>   Whatever the target version, the target is now that point release or
>   later, and the table's ".7 out" and ".2 out" are two months old.
> - **Corrected: the renames do not fail on restart.** The original section
>   said the renamed options would stop the config from parsing after the
>   daemon restarts. Slurm's source says otherwise; the section below is
>   rewritten with the lines it is based on.
> - **Corrected: the release date.** 26.05.0 was published on 26 May 2026,
>   not 14 July. The 14 July releases were 26.05.2 and 25.11.7
>   ([releases](https://github.com/SchedMD/slurm/releases)).
> - **Corrected: the REST API row** of the table, against the release notes.
> - **Withdrawn: a promise.** The post ended by promising the full upgrade
>   runbook "as its own repo". That repository was never published.

I had a plan. Move a 250-node cluster from 25.05 to 25.11, write it up, ship it.

Then I checked the release list and found a newer major release was already
out: 26.05.0 on 26 May, and 26.05.2 alongside 25.11.7 on 14 July. *[Corrected;
this sentence originally said 26.05 had shipped on 14 July.]* And 26.05 upgrades
**directly** from 25.05 — which means the version I was carefully planning to
land on is not the only option, and possibly not the right one.

So this is the comparison I actually needed: three versions, what breaks between
them, and which one a cluster with one head node and 250 compute nodes should
be aiming at.

## The short version

As of 26 July 2026, with the REST row corrected in September:

| | 25.05 | 25.11 | 26.05 |
| --- | --- | --- | --- |
| Status (26 July) | current on my cluster | stable, .7 out | **latest**, .2 out |
| Status (26 September) | 25.05.9 (security) | 25.11.8 (security) | 26.05.4 (security) |
| Direct upgrade from | — | 25.05, 24.11, 24.05 | 25.11, 25.05, 24.11 |
| Renamed config options | — | `JobContainerType` → `NamespaceType` | `ExclusiveUser`, `ExclusiveTopo` → `Exclusive=` |
| Prometheus | none | basic openmetrics | **+ GPU allocation stats** |
| cgroup layout | JobId | JobId | **SLUID** |
| REST API | v0.0.43 added; v0.0.40 deprecated, removal in 25.11 | v0.0.44 added; v0.0.41 deprecated, removal in 26.05 | v0.0.45 added; v0.0.42 deprecated, removal in 26.11 |

The REST row is taken line for line from each branch's `RELEASE_NOTES.md`
([25.05](https://github.com/SchedMD/slurm/blob/slurm-25.05/RELEASE_NOTES.md),
[25.11](https://github.com/SchedMD/slurm/blob/slurm-25.11/RELEASE_NOTES.md),
[26.05](https://github.com/SchedMD/slurm/blob/slurm-26.05/RELEASE_NOTES.md)).
The original row said "v0.0.41 deprecated" for 25.05; 25.05 deprecated v0.0.40.

Both 25.11 and 26.05 are reachable in one hop from 25.05. That is the whole
decision: one change window or two.

## The renamed options, and what they actually do on restart

*[This section replaces the original "The renames that fail on restart",
which was wrong.]*

Two renames, one per version:

**25.11 renamed `JobContainerType` to `NamespaceType`** ("NamespaceType
replaces JobContainerType in slurm.conf", 25.11 release notes). The
`job_container` plugin interface became `namespace`, with a new
`namespace/linux` plugin that handles filesystem, PID, and user namespaces. If
you do per-job private `/tmp`, this line is in your config.

**26.05 replaced `ExclusiveUser` and `ExclusiveTopo`** on partitions with a
single `Exclusive=[NO|NODE|USER|TOPO]` (26.05 release notes).

The original post said both would make a config that "parses fine today and
does not parse after the daemon restarts". Slurm's source does not do that:

- On the `slurm-25.11` branch, `src/common/read_config.c` still reads
  `JobContainerType`. When slurmctld finds it, it logs
  *"JobContainerType has been replaced with NamespaceType and will be removed
  in a future release, please update your config."* and uses the value as the
  namespace plugin if `NamespaceType` is not set (lines 4070–4079 at
  [`6b5e6b5`](https://github.com/SchedMD/slurm/blob/6b5e6b5550d0bddd38aff08c0bf666d9f048f84b/src/common/read_config.c#L4070-L4079)).
  The `slurm-26.05` branch does the same (lines 4223–4225 at
  [`093a880`](https://github.com/SchedMD/slurm/blob/093a8804db85dcc391318f8900e6f1a5977b08db/src/common/read_config.c#L4223-L4225)).
- On the `slurm-26.05` branch, `ExclusiveUser` and `ExclusiveTopo` are still
  in the partition option table next to the new `Exclusive` key, and are still
  read as booleans (lines 1191–1193 and 1384–1388 at
  [`093a880`](https://github.com/SchedMD/slurm/blob/093a8804db85dcc391318f8900e6f1a5977b08db/src/common/read_config.c#L1191-L1193)).

So today these are renamed options that keep working, one of them with a
deprecation warning, and will be removed "in a future release". Branch heads
read on 26 September 2026. I have not run either version with the old names,
and I have not tested what happens when they are finally removed.

They are still worth a `grep` before the change window, because the removal
will come in some later release and the warning is easy to miss in a
slurmctld log during an upgrade:

```bash
grep -rnE 'JobContainerType|ExclusiveUser|ExclusiveTopo' /etc/slurm/
```

## The one that will break your tooling

This is the change I would have missed, and it is the expensive one. From the
26.05 release notes:

> cgroup/v2 directory structures are now keyed off of SLUID and not the JobId.

Read that again if you own any monitoring that walks cgroups.

The standard way to attribute a process — or a GPU, or an InfiniBand counter —
back to a Slurm job is to walk the job's cgroup directory and match PIDs. Every
job-aware exporter I know of does some version of this. On a default 26.05 node
the job directory is named by the SLUID itself, with no `job_` prefix:
`cgroup.conf(5)`'s `CgroupJobIdPaths` (default `no`) gives
`/sys/fs/cgroup/system.slice/slurmstepd.scope/sEKNKTV3WPV500/` as the new form
and `.../job_123/` as the one you get back with `CgroupJobIdPaths=yes`
([cgroup.conf](https://slurm.schedmd.com/cgroup.conf.html)). Anything parsing a
job ID out of the directory name gets a value that is not a job ID, or finds
no job directory at all.

It will not error. It will return the wrong number, or nothing, and your
dashboards will go quietly flat.

I have a direct stake in this one: I have been building a GPU-waste reaper whose
next milestone is exactly this cgroup walk, and the note above means the
implementation I sketched is already obsolete for anyone on 26.05. Better to
learn that from a release note than from a silent regression six months in.
*[Update, 27 September 2026: that milestone was not taken up. The
[reaper](/projects/gpu-reaper/) skips GPU jobs on shared nodes instead of
attributing them, its README calls the cgroup walk out of scope, and no tool
in this set maps GPU processes to jobs yet.]*
(The [InfiniBand exporter](/projects/ib-slurm-exporter/) handles all three
layouts; its 26.05 handling is implemented from the documentation and tested
on synthetic trees, not validated on a live 26.05 node.)

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

For this cluster, 26.05 — now at 26.05.4 or later, because of the September
security fixes.

The upgrade path is the same length either way — one hop from 25.05 — and taking
25.11 means doing the whole exercise again in a few months to get to a release
that is already out. The 250-node `slurmd` roll is the expensive part, and it
costs the same whichever target you pick. Paying it twice for no reason is the
easiest mistake to avoid here.

The argument against is real, though: in July 25.11 had had eight releases
(.0 to .7) and 26.05 three (.0 to .2). If your cluster is the one people ship
from and you cannot tolerate being an early adopter, take 25.11 now and 26.05
in six months. That is a legitimate risk call, not a cop-out — it just costs you
two change windows.

What I would not do is default to 25.11 because it was the plan before I looked.

## Order of operations

Nothing exotic, and unchanged across both versions:

1. `grep` the config for `JobContainerType`, `ExclusiveUser`, `ExclusiveTopo`,
   and move to the new names while the old ones still work.
2. Audit anything talking REST for a pinned API version. v0.0.41 is removed in
   26.05 (the 25.11 release notes say so); v0.0.42 is deprecated there and goes
   in 26.11.
3. **Audit anything walking cgroups.** This is the new one, and it is the one
   that fails silently.
4. Back up `slurmdbd`. The database migration is the step with no easy undo, and
   it is the step people skip because it has always worked before.
5. `slurmdbd` → verify → `slurmctld` → verify.
6. Roll `slurmd` in batches, draining ahead of each. Never a compute node ahead
   of the controller.
7. New features *after* the version move is stable. Expedited requeue and the
   GPU metrics endpoints are not part of the upgrade; they are the next change.

*[Withdrawn: the original post promised the full runbook — node batching,
rollback triggers — "as its own repo". It was never published.]*

## What this is and isn't

This is release notes plus a decision, not a war story. I have not run 25.05 →
26.05 on 250 nodes yet. When I do, the useful post is the delta between this
plan and what actually happened, because that gap is where the real content
always is.

If you have already made either hop, I would like to know what bit you —
particularly whether the cgroup change broke anything you did not expect.

**Sources:** [Slurm release notes](https://slurm.schedmd.com/release_notes.html) ·
[26.05 RELEASE_NOTES.md](https://github.com/SchedMD/slurm/blob/slurm-26.05/RELEASE_NOTES.md) ·
[25.11 RELEASE_NOTES.md](https://github.com/SchedMD/slurm/blob/slurm-25.11/RELEASE_NOTES.md) ·
[25.05 RELEASE_NOTES.md](https://github.com/SchedMD/slurm/blob/slurm-25.05/RELEASE_NOTES.md) ·
[SchedMD releases on GitHub](https://github.com/SchedMD/slurm/releases) ·
[26.05.2 / 25.11.7 announcement](https://lists.schedmd.com/mailman3/hyperkitty/list/slurm-users@lists.schedmd.com/message/RBO6LEZNM754W22473U3XW643OEPPVS6/) ·
[cgroup.conf](https://slurm.schedmd.com/cgroup.conf.html) ·
[Upgrade guide](https://slurm.schedmd.com/upgrades.html)
