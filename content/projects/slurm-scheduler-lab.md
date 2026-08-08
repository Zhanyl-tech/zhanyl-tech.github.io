---
title: "Slurm Scheduler Lab"
date: 2026-07-26
description: "Test Slurm priority and backfill policy against a job trace before it reaches a live controller."
summary: "Test Slurm priority and backfill policy against a job trace before it reaches a live controller."
tags: [slurm, hpc, scheduling, backfill, python]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/slurm-scheduler-lab"
weight: 5
ShowToc: false
---

**[github.com/Zhanyl-tech/slurm-scheduler-lab](https://github.com/Zhanyl-tech/slurm-scheduler-lab)** · MIT · Python 3.10+

Changing `PriorityWeightFairshare` on a production cluster is a slow, expensive
experiment: the feedback loop is days long, the blast radius is everyone's
queue, and the only rollback signal is people complaining. This runs the same
policy against a workload in about a second.

![Four node timeline showing a reservation at shadow time, one job backfilled into a gap, and one rejected for crossing the reservation](/images/diagrams/backfill.svg)

## What it models

**Multifactor priority** — the real formula from `priority/multifactor`, with
age, fairshare, job size, partition, and QOS factors each normalised to `[0,1]`
so the weights alone decide what the queue optimises for. Fairshare uses
Slurm's classic `F = 2^(-U/S)` with exponential usage decay.

**EASY backfill** — priority-ordered dispatch with shadow-time reservations. The
scheduler is never allowed to read a job's true runtime, only its requested
`time_limit`, which is what makes over-requesting visible as a measurable cost.

## Using it on a real cluster

```bash
sacct -a -X --parsable2 --starttime=now-30days \
      --format=JobID,Account,Submit,Elapsed,Timelimit,NNodes,ReqCPUS,ReqTRES \
      > trace.txt

schedlab --sacct trace.txt --slurm-conf /etc/slurm/slurm.conf --nodes 64
```

It reads `PriorityWeight*` straight out of the config you are about to deploy,
so you can compare the config you have against the config you are considering.

## What it found

| | backfill off | backfill on |
| --- | --- | --- |
| CPU utilization | 72.2 % | 83.6 % |
| Mean wait | 1913.0 min | 373.7 min |
| Median wait | 2303.3 min | 131.9 min |
| Bounded slowdown | 373.18 | 55.66 |

Sweeping `PriorityWeightJobsize` across 100,000x moves mean wait about 40%.
Backfill moves it 400%. The number that actually explains the queue turned out
to be time-limit accuracy — jobs using ~32% of the wall-clock they request.

Written up in **[Your Slurm priority weights matter less than your users' time
limits](/experiments/2026-07-26-slurm-backfill-time-limits/)**.

## Scope

Deliberately not a Slurm reimplementation: first-fit node selection with no
topology awareness, aggregate rather than per-node backfill reservations, flat
fairshare, no preemption or gang scheduling. Good for comparing policies
against each other on the same workload; not for predicting absolute wait times.

23 tests cover reservation safety, fairshare maths, capacity invariants, and
determinism across identical seeds.
