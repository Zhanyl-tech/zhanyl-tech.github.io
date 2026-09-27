---
title: "Slurm Scheduler Lab"
date: 2026-07-26
lastmod: 2026-09-27
description: "A discrete-event model of Slurm's multifactor priority, Fair Tree fairshare, backfill and preemption, for testing scheduling policy against a trace before it reaches a live controller."
summary: "A discrete-event model of Slurm's multifactor priority, Fair Tree fairshare, backfill and preemption, for testing scheduling policy before it reaches a live controller."
tags: [slurm, scheduling, backfill, simulation, python]
status: "Simulator · no live slurmctld behind its numbers"
stage: "built"
repo: "https://github.com/Zhanyl-tech/slurm-scheduler-lab"
weight: 2
ShowToc: true
---

**[github.com/Zhanyl-tech/slurm-scheduler-lab](https://github.com/Zhanyl-tech/slurm-scheduler-lab)** · Python · MIT

<p class="project-status"><span class="status status-built">built</span>
A simulator. Its semantics come from Slurm's documentation and source (pinned
to a commit in the README); nothing here has been replayed against a real
<code>slurmctld</code>, and every number on this page is from its synthetic
workload unless it says otherwise.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26 (conservative backfill, Fair Tree, preemption, S0). Merge or push
that branch before publishing, or the page will describe code readers cannot
see. -->

Changing `PriorityWeightFairshare` on a production cluster is a slow, expensive
experiment: the feedback loop is days long, the blast radius is everyone's
queue, and the only rollback signal is people complaining. This runs the same
policy against a few hundred jobs in about a second, and reads the settings
straight out of the `slurm.conf` you are about to deploy.

![EASY backfill on a four-node timeline: a reservation at shadow time, one job backfilled into a gap and one rejected for crossing the reservation; below it, one synthetic seed of the simulator in EASY mode](/images/diagrams/backfill.svg)

## What it models

- **Multifactor priority**, the `priority/multifactor` formula, with each
  factor normalised to [0, 1] so the weights alone decide what the queue
  optimises for. Integer priorities, as Slurm stores them.
- **Fairshare, both of Slurm's algorithms.** Fair Tree by default, because it
  is what an unconfigured controller runs; classic `2^(-U/S)` with
  `PriorityFlags=NO_FAIR_TREE`. Usage accrues and decays on
  `PriorityCalcPeriod` ticks, so priorities lag the way they do on a real
  controller.
- **Backfill, two ways.** The default is the shape of Slurm's `sched/backfill`:
  a main scheduler that stops at its first blocked job, plus a backfill cycle
  every `bf_interval` that plans every pending job into a per-node timeline
  and starts a job only if it moves no higher-priority job's planned start,
  bounded by `bf_max_job_test`, `bf_window` and `bf_resolution`. Textbook EASY
  backfill (protect only the first blocked job) is kept as an option.
- **Preemption**, off by default as in Slurm: `preempt/partition_prio` and
  `preempt/qos`, `CANCEL` and `REQUEUE`, and `GraceTime`, with work lost and
  grace-locked CPU- and GPU-hours reported.
- **The scheduler never reads a job's true runtime**, only its requested time
  limit, and a test enforces that across whole simulations. An `sacct` trace
  keeps its recorded `Timelimit`; it is never replaced by `Elapsed`.
- **The Slurm side of a cross-substrate comparison (S0).** It can replay a
  trace from [k8s-gpu-scheduler-lab](/projects/k8s-gpu-scheduler-lab/) on the
  same heterogeneous fleet and score it under that lab's metric definitions,
  including a shared "Definition C" fragmentation function checked against a
  common golden vector. As a model only; the README lists what is and is not
  comparable, starting with the fact that Slurm allocates a gang atomically.

Settings the model does not implement are printed as warnings rather than
silently ignored.

## Point it at your cluster

```bash
sacct -a -X --parsable2 --starttime=now-30days \
      --format=JobID,User,Account,Submit,Elapsed,Timelimit,NNodes,ReqCPUS,ReqTRES \
      > trace.txt

schedlab --slurm-conf /etc/slurm/slurm.conf --sacct trace.txt --nodes 64 --cpus 32 --gpus 4
```

No controller is touched. `--sched-params` tries a `SchedulerParameters`
change without editing the config, and `--sweep` walks one priority weight.

## What it shows, and how much to trust it

On one synthetic seed the effect of backfill looks dramatic:

```
$ schedlab --compare-backfill --jobs 300 --seed 5      # 16 nodes × 8 CPU / 2 GPU

backfill OFF   cpu utilization 72.3 %   mean wait 1896.7 min
backfill ON    cpu utilization 83.0 %   mean wait  396.1 min
```

One seed is an anecdote, and this project learned that the hard way: an earlier
write-up drew "priority weights barely matter" from a single seed of version
0.1, and it did not survive twenty ([correction](/experiments/2026-07-26-slurm-backfill-time-limits/)).
Over seeds 0–19 of the current model, run on 2026-09-27:

| | median | range |
| --- | --- | --- |
| mean wait, backfill off ÷ on | 3.84× | 2.17–5.71× |
| CPU utilisation gain from backfill | +16.4 points | 5.1–28.8 |
| mean wait, largest ÷ smallest across `PriorityWeightJobsize` 0 / 1k / 10k / 100k | 3.18× | 2.15–3.87× |

Backfill cut mean wait on every seed; the job-size weight moved it by a
comparable factor, and more than backfill did on 6 of the 20. Each row is
`schedlab --compare-backfill --jobs 300 --seed s` and
`schedlab --sweep jobsize --jobs 300 --seed s` for each seed, read from the
text report. Exact time limits (`--time-limit-model exact`, over seeds 0–9)
raised mean CPU utilisation from 84.2% to 86.3%, higher on 7 of the 10 seeds,
and mean wait from 489.1 to 656.6 minutes, higher on 9 of 10
(`schedlab --jobs 300 --seeds 10`, with and without that flag): accurate
requests bought some throughput and cost waiting on this workload.
`--seeds N` prints the spread for any comparison, and the README runs every
claim it makes through it.

<!-- OWNER: these figures were produced on 2026-09-27 from slurm-scheduler-lab's
working tree: commit c02b52f plus uncommitted changes, working-tree fingerprint
0c64a952cad1 (the recipe in that README's "Running S0" section, applied to this
repository). Before this change they read 89.9% / 442.5 min, 3.89x, +16.0 and
3.12x, from an earlier state of the same uncommitted tree, before time limits
were rounded to whole minutes. When the lab is committed, re-run the forty
per-seed commands at that commit and name it here. -->

## Scope

Deliberately not a Slurm reimplementation. First-fit node selection with no
topology-aware placement; a flat, one-level account tree; no job arrays,
heterogeneous jobs, licences, reservations or gang time-slicing; Slurm's own
wall-clock costs (`bf_max_time`, RPC load) are not modelled. Good for comparing
policies against each other on the same workload, not for predicting absolute
wait times on your cluster. The README lists every simplification and the
source line each modelled rule comes from.
