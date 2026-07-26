---
title: "Your Slurm Priority Weights Matter Less Than Your Users' Time Limits"
date: 2026-07-26
description: "I built a simulator to tune Slurm priority weights. It kept telling me the weights were not the problem."
tags: [slurm, hpc, scheduling, backfill, gpu, cluster]
summary: "I built a simulator to tune Slurm priority weights. It kept telling me the weights were not the problem."
ShowToc: false
draft: false
---

I wanted to change `PriorityWeightFairshare` on a cluster and could not justify
the experiment. The feedback loop is days long, the blast radius is everyone's
queue, and the only rollback signal is people complaining in Slack.

So I wrote the thing that lets you try it offline:
[**slurm-scheduler-lab**](https://github.com/Zhanyl-tech/slurm-scheduler-lab).
It implements Slurm's `priority/multifactor` formula and EASY backfill, reads
`PriorityWeight*` straight out of a `slurm.conf`, and replays either a synthetic
workload or a real trace from `sacct`.

Then it kept telling me I was tuning the wrong thing.

## First, backfill is doing most of the work

Baseline, 300 jobs on 16 nodes:

```
backfill OFF                          backfill ON
  cpu utilization      72.2 %           cpu utilization      83.6 %
  mean wait          1913.0 min         mean wait           373.7 min
  median wait        2303.3 min         median wait         131.9 min
  bounded slowdown    373.18            bounded slowdown     55.66
```

An 11-point utilization swing and a 5x cut in mean wait. Median drops 17x,
because backfill disproportionately rescues the small jobs that were stuck
behind a wide one. None of this is new — it's why EASY backfill won in the
nineties — but it sets the scale for everything after it.

## Then the weights, which move much less

Sweeping `PriorityWeightJobsize` across four orders of magnitude:

```
weight=0        util  87.3%  mean wait  352.9 min  p95 1978.4 min  slowdown 52.08
weight=1000     util  90.6%  mean wait  348.2 min  p95 1879.4 min  slowdown 58.08
weight=10000    util  83.6%  mean wait  373.7 min  p95 1817.7 min  slowdown 55.66
weight=100000   util  93.4%  mean wait  496.7 min  p95 1904.7 min  slowdown 60.79
```

There is a real tradeoff here, and it is the one you would predict: at
`weight=100000` the machine is fullest (93.4%) and the queue is slowest (497
min mean wait). Big jobs go first, utilization looks great on the dashboard, and
everything small waits behind them.

But look at the range. Across a 100,000x change in the weight, mean wait moves
by about 40%. Backfill moved it by 400%.

`PriorityWeightFairshare` was flatter still — it redistributes wait *between*
accounts, which is its job, without changing the total much.

## The number that actually explains the queue

Both runs above report the same line:

```
time-limit accuracy    32.2 %
```

Jobs use about a third of the wall-clock they ask for. That is a property of my
generator, not a measurement — I set the padding to ~3x because that is the
range published trace studies keep reporting. Whether it holds on your cluster
is a one-line `sacct` query, and I'd rather you check than take my word for it.

It matters because **backfill plans against what users request, not what their
jobs need.** The scheduler computes a shadow time — the earliest moment the
blocked job can start, assuming every running job runs to its full limit — and
then only backfills work it can *prove* will not delay that reservation.

A job that will really take 50 seconds but claims 500 is unprovable. It sits.

That's the case I pinned in a test, because it's the whole argument:

```python
def test_backfill_plans_against_time_limit_not_true_runtime():
    honest = [..., job(3, 2, duration=50, nodes=1, time_limit=50)]
    padded = [..., job(3, 2, duration=50, nodes=1, time_limit=500)]

    assert honest[2].start_time == pytest.approx(2.0)
    assert padded[2].start_time > honest[2].start_time
```

Identical real runtimes. Identical cluster. Identical priority weights. The only
difference is what the user typed into `--time`, and one of them backfills
instantly while the other waits for the reservation to clear.

## What I'd do differently

I came in expecting to ship a weights change. What I'd actually do first:

1. **Measure `time-limit accuracy` on the real trace.** One `sacct` query. If
   it's near 30%, that's the finding.
2. **Fix the defaults before the weights.** A partition `DefaultTime` that
   matches reality beats any weight I sweep here.
3. **Then tune weights** — for *who waits*, which is what they genuinely
   control, not *how long the queue is*.

The simulator is on
[GitHub](https://github.com/Zhanyl-tech/slurm-scheduler-lab). Point it at your
own `slurm.conf` and `sacct` output:

```bash
sacct -a -X --parsable2 --starttime=now-30days \
      --format=JobID,Account,Submit,Elapsed,Timelimit,NNodes,ReqCPUS,ReqTRES \
      > trace.txt

schedlab --sacct trace.txt --slurm-conf /etc/slurm/slurm.conf --nodes 64
```

I'd genuinely like to know whether the 32% holds up on a production trace, or
whether my synthetic workload is flattering itself.

## Caveats

This is a model, not a controller. Node selection is first-fit with no topology
awareness, backfill reservations are computed on aggregate CPU/GPU counts rather
than per node, fairshare is flat rather than hierarchical, and there's no
preemption or gang scheduling. Those simplifications are listed in the README
because they bound what the numbers above are allowed to claim: they're good for
comparing *policies against each other* on the same workload, and not for
predicting absolute wait times on your cluster.
