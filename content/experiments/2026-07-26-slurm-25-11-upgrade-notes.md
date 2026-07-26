---
title: "Reading the Slurm 25.11 Release Notes as an Operator"
date: 2026-07-26
description: "One rename will break your slurm.conf, slurmctld speaks Prometheus natively now, and expedited requeue changes how you think about node failure."
tags: [slurm, hpc, upgrade, prometheus, cluster-operations]
summary: "One rename will break your slurm.conf, slurmctld speaks Prometheus natively now, and expedited requeue changes how you think about node failure."
ShowToc: false
draft: false
---

Slurm 25.11 is out, and it upgrades directly from 25.05, 24.11, and 24.05. I'm
planning a 25.05 → 25.11 move on a cluster with one head node and 250 compute
nodes, so I read the release notes the way you read them when you own the
pager: what breaks, what I have to schedule downtime for, and what I get to
delete afterwards.

Three things stood out.

## The rename that will break your config

`JobContainerType` is now `NamespaceType`.

The `job_container` plugin interface has been renamed to `namespace`, and a new
`namespace/linux` plugin replaces it with support for filesystem, PID, and user
namespaces. If your `slurm.conf` carries `JobContainerType=job_container/tmpfs`
— and if you do per-job private `/tmp`, it does — that line does not survive the
upgrade.

This is the one to grep for first:

```bash
grep -rn 'JobContainerType' /etc/slurm/
```

It's a mechanical fix, but it's a config-parse failure on a control daemon
restart, which is the worst time to discover it. On a 250-node cluster the
`slurm.conf` has to be consistent everywhere, so this lands in the same change
window as the daemon upgrade rather than after it.

While you're in there, `SlurmdParameters=conmgr_threads` has a new default of
6. If you tuned that for a large node count, your explicit value still wins, but
the new default is worth knowing when you're reading someone else's config.

## slurmctld exports Prometheus directly now

25.11 adds native OpenMetrics export from `slurmctld`.

I have opinions about this one, because I've been building the opposite thing.
The usual setup is a sidecar exporter that shells out to `sinfo`/`squeue`,
parses the text, and re-exports it — which is fragile in exactly the way
text-scraping always is, and adds a process per cluster you have to monitor in
order to monitor the cluster.

Native export removes that layer for the metrics `slurmctld` already knows:
queue depth, job states, node states, scheduler cycle timing.

What it does *not* give you is correlation with anything below the scheduler.
`slurmctld` knows a job is running on 8 nodes; it does not know that those nodes
are burning retries on `mlx5_0` and that's why the all-reduce is slow. That
still needs a node-local exporter reading cgroups and matching PIDs against
InfiniBand counters. So this narrows what a custom exporter should do rather
than eliminating it — which is useful, because the narrower version is the part
that was actually load-bearing.

If you're running a scrape sidecar today, 25.11 is a good moment to check how
much of it is now redundant.

## Expedited requeue

New `--requeue=expedite` mode for batch jobs. Jobs marked this way automatically
requeue on node failure, or when the batch script exits non-zero *and* one or
more Epilog scripts fail. On requeue they're treated as the highest priority job
in the system, and their previously allocated nodes are prevented from launching
other work.

That last clause is the interesting one. It's not just a priority boost — it's a
soft reservation on the nodes the job was already on, which is what you want for
a long training run that died at hour 40 and would otherwise have to re-queue
behind everything that accumulated while it ran.

The Epilog condition is the part I'd read twice before enabling it broadly. A
failing Epilog is often how you find out a node is sick. Coupling "Epilog
failed" to "requeue at top priority, and hold those nodes" means a genuinely bad
node can hold an expedited job in a loop. If you enable this, the node health
check in your Epilog needs to drain decisively rather than just exit non-zero.

## The rest of the list

Worth knowing, less likely to change your plan:

| Change | Why it matters |
| --- | --- |
| Hierarchical Resources Mode 3 | Sums usage from lower levels automatically |
| `SlurmctldParameters=enable_async_reply` | Experimental; offloads RPC replies to the kernel to free worker threads |
| Reservation `AllowQOS` / `AllowPartition` | Finer reservation access control |
| `JobCompPassScript`, `StoragePassScript` | Password rotation without a config edit |
| `MaxPurgeLimit`, `DisableArchiveCommands` in `slurmdbd.conf` | Bounds purge blast radius |
| `squeue --running-over` / `--running-under` | Time filters — useful for finding stuck jobs |
| `--consolidate-segments` / `--spread-segments` | Segment placement control on salloc/sbatch/srun |
| `node_features/knl_generic` | **Removed.** Only matters if you still run Knights Landing |
| v0.0.41 REST endpoints | **Deprecated**, removal planned for 26.05 |

That last row is the one with a clock on it. If anything you own talks to the
Slurm REST API — a dashboard, a submission portal, a CI integration — check
which version it pins. Deprecated in 25.11, gone in 26.05, and 26.05 is the
release after next.

## What I'm actually doing with this

Upgrade order for a single-controller cluster is unchanged: `slurmdbd` first,
then `slurmctld`, then `slurmd` across the fleet, and never a compute node ahead
of the controller. With 250 nodes the `slurmd` roll is the long pole, and it's
the part that tolerates being done in batches.

My plan, in the order I'll do it:

1. `grep` the config for `JobContainerType` and every removed parameter.
2. Audit anything speaking REST for a v0.0.41 pin.
3. Back up `slurmdbd` before touching it. The database migration is the step
   with no easy undo.
4. Upgrade `slurmdbd`, verify, then `slurmctld`.
5. Roll `slurmd` in batches, draining ahead of each.
6. Only then look at native OpenMetrics and expedited requeue — new features go
   in after the version move is stable, not during it.

I'm writing that plan up properly, with the node-batching and rollback
triggers, as a separate repo.

## Caveat

This is a reading of the release notes and an upgrade plan, not a report from
the other side of one. I have not yet run 25.05 → 25.11 on the 250-node cluster.
When I do, the interesting content will be the difference between this plan and
what actually happened — which is usually where the real post is.

If you've already made this move, I'd like to know what bit you.

**Sources:** [Slurm 25.11.0 announcement](https://www.schedmd.com/slurm-version-25-11-0-is-now-available/) ·
[RELEASE_NOTES.md at slurm-25.11](https://github.com/SchedMD/slurm/blob/slurm-25.11/RELEASE_NOTES.md) ·
[Upgrade guide](https://slurm.schedmd.com/upgrades.html)
