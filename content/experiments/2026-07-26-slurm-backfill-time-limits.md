---
title: "Slurm Backfill vs. Priority Weights on a Synthetic Workload: What One Seed Showed, and What Twenty Did Not"
date: 2026-07-26
lastmod: 2026-09-27
description: "Corrected September 2026. In my simulator backfill has a large effect on every seed. The original claim that priority weights barely matter came from one seed, and the time-limit claim was never measured."
tags: [slurm, hpc, scheduling, backfill, simulation]
summary: "Corrected September 2026. Backfill has a large effect on every seed; the claim that priority weights barely matter came from one seed, and the time-limit claim was never measured."
ShowToc: true
draft: false
---

> **Correction, 26 September 2026.** This post was first published on 26 July
> 2026 under the title *"Your Slurm Priority Weights Matter Less Than Your
> Users' Time Limits"*. Four things in it were wrong, and the site repeated
> them elsewhere:
>
> 1. **It was one synthetic seed, not a trace.** Every number came from the
>    simulator's synthetic generator: 300 jobs on 16 nodes, **seed 5**, with
>    simulator version 0.1 (commit `c02b52f`). The post never said which seed,
>    and other pages called the result "measured" on "real job traces".
> 2. **"The weights barely matter" does not survive other seeds.** Over seeds
>    0–19 of the same code, sweeping `PriorityWeightJobsize` moved mean wait
>    by a median **3.06×** (range 1.43–4.27×). Seed 5 was the *smallest*
>    effect of the twenty, and on 3 of the 20 seeds the weight sweep moved mean
>    wait more than turning backfill on did.
> 3. **The time-limit claim was never measured.** "Time-limit accuracy 32.2%"
>    is the padding the generator puts on the input, not an observation. When a
>    later version of the simulator measured it (below), exact time limits
>    raised utilisation *and* raised mean wait.
> 4. **"A 100,000× change in the weight" was arithmetic I got wrong.** The
>    sweep is 0, 1,000, 10,000 and 100,000; the non-zero range is 100×.
>
> What does hold: **on this synthetic model, backfill cuts mean wait by a large
> factor on every one of the twenty seeds.** The sections below give the
> numbers, the commands, and then the original text with the wrong claims
> marked. Everything here is a simulator; no live `slurmctld` was involved.

## What twenty seeds show

Each row is one command per seed, run for this correction (the v0.1 rows on
2026-09-26, the current rows re-run on 2026-09-27). "Ratio"
is mean wait with backfill off divided by mean wait with it on; "sweep" is the
largest mean wait across `PriorityWeightJobsize` ∈ {0, 1000, 10000, 100000}
divided by the smallest.

| simulator | backfill: mean-wait ratio | backfill: CPU-utilisation gain | jobsize sweep: mean-wait ratio | sweep > backfill |
| --- | --- | --- | --- | --- |
| v0.1 (`c02b52f`, EASY, classic fairshare) | median 4.65×, range 2.27–6.92× | median +16.1 pts, range 7.6–32.5 | median 3.06×, range 1.43–4.27× | 3 of 20 seeds |
| current (unreleased, conservative backfill, Fair Tree) | median 3.84×, range 2.17–5.71× | median +16.4 pts, range 5.1–28.8 | median 3.18×, range 2.15–3.87× | 6 of 20 seeds |

Per seed *s* in 0–19: `schedlab --compare-backfill --jobs 300 --seed s` and
`schedlab --sweep jobsize --jobs 300 --seed s`, with the mean-wait lines read
from the CLI's text report. The v0.1 rows ran on a `git archive` of commit
`c02b52f`. The current rows ran on the simulator's next version as it stood on
2026-09-27, before it was committed or released. They will be re-run and pinned
to a commit when it is released; until then they cannot be reproduced exactly.
(An earlier state of that unreleased code, before it rounded invented time
limits up to whole minutes as Slurm does, gave median 3.89×, +16.0 points and
3.12× here, and 442.5 minutes for seed 5 with backfill on.)
<!-- OWNER: pin the "current" rows before this correction goes live. They
were re-run on 2026-09-27 against slurm-scheduler-lab's working tree: HEAD
c02b52f (the v0.1 commit) plus uncommitted changes on its improve/2026-09
branch, working-tree fingerprint 0c64a952cad1 (SHA-256 of `git diff HEAD
--binary` followed by the sha256 lines of each untracked file in sorted order,
first 12 hex digits: the recipe in that repository's README, "Running S0").
The script that produced them is
.tools/consistency-pass/ssl_seeds.py in the workspace. Once the scheduler-lab
work is committed: re-run the forty per-seed commands and the time-limit
comparison at that commit, update every table in this post, the medians here,
on about.md ("a median 3.8x across 20 seeds"), projects/_index.md and
slurm-scheduler-lab.md, then replace "unreleased" in the summary table and the
sentence above with the commit hash or release tag, as the v0.1 rows do with
c02b52f. Point the README link under "Slurm is not EASY" at that tag.
scripts/check_content.py refuses a published page that names a working branch
outside a comment. -->

<details>
<summary>Per-seed numbers (all forty runs)</summary>

| seed | v0.1 mean wait, off → on (min) | v0.1 backfill ratio | v0.1 sweep min–max (min) | v0.1 sweep ratio | current mean wait, off → on (min) | current backfill ratio | current sweep min–max (min) | current sweep ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1298.7 → 280.5 | 4.63× | 238.0–798.1 | 3.35× | 1312.4 → 294.3 | 4.46× | 252.9–614.8 | 2.43× |
| 1 | 1285.4 → 252.7 | 5.09× | 252.7–654.5 | 2.59× | 1190.7 → 469.8 | 2.53× | 330.1–811.4 | 2.46× |
| 2 | 1630.2 → 267.0 | 6.11× | 252.2–667.8 | 2.65× | 1595.2 → 279.6 | 5.71× | 236.5–659.3 | 2.79× |
| 3 | 1347.4 → 575.0 | 2.34× | 287.8–1220.3 | 4.24× | 1377.8 → 579.9 | 2.38× | 320.6–1228.5 | 3.83× |
| 4 | 1468.2 → 313.8 | 4.68× | 287.9–703.6 | 2.44× | 1430.7 → 354.5 | 4.04× | 289.5–623.1 | 2.15× |
| 5 | 1913.0 → 373.7 | 5.12× | 348.2–496.7 | 1.43× | 1896.7 → 396.1 | 4.79× | 376.3–1304.1 | 3.47× |
| 6 | 2144.8 → 943.8 | 2.27× | 388.5–1659.3 | 4.27× | 2096.1 → 966.2 | 2.17× | 484.9–1655.2 | 3.41× |
| 7 | 1235.6 → 236.5 | 5.22× | 202.8–686.3 | 3.38× | 1398.7 → 324.1 | 4.32× | 249.5–736.8 | 2.95× |
| 8 | 1372.4 → 329.3 | 4.17× | 247.8–896.0 | 3.62× | 1270.8 → 468.4 | 2.71× | 280.6–900.9 | 3.21× |
| 9 | 1741.9 → 501.0 | 3.48× | 338.1–1419.7 | 4.20× | 1829.6 → 758.1 | 2.41× | 348.8–1349.8 | 3.87× |
| 10 | 1840.5 → 581.1 | 3.17× | 446.1–1078.7 | 2.42× | 2113.9 → 542.5 | 3.90× | 448.4–1110.3 | 2.48× |
| 11 | 1680.0 → 423.3 | 3.97× | 346.1–1040.6 | 3.01× | 1578.1 → 542.3 | 2.91× | 372.0–1189.4 | 3.20× |
| 12 | 1816.1 → 346.9 | 5.24× | 335.9–1129.7 | 3.36× | 1978.3 → 523.9 | 3.78× | 344.8–1219.2 | 3.54× |
| 13 | 1407.9 → 343.9 | 4.09× | 295.3–744.3 | 2.52× | 1454.2 → 331.3 | 4.39× | 311.3–865.4 | 2.78× |
| 14 | 1536.4 → 360.0 | 4.27× | 311.3–1031.3 | 3.31× | 1352.3 → 433.1 | 3.12× | 342.5–1080.2 | 3.15× |
| 15 | 1635.5 → 236.3 | 6.92× | 233.1–433.0 | 1.86× | 1504.7 → 302.0 | 4.98× | 286.0–845.1 | 2.95× |
| 16 | 1627.6 → 302.2 | 5.39× | 253.7–762.5 | 3.01× | 1623.4 → 353.6 | 4.59× | 305.2–1087.7 | 3.56× |
| 17 | 1759.7 → 345.0 | 5.10× | 327.7–1161.1 | 3.54× | 1687.7 → 449.8 | 3.75× | 362.9–1194.0 | 3.29× |
| 18 | 1103.8 → 263.8 | 4.18× | 241.1–719.2 | 2.98× | 1180.7 → 350.3 | 3.37× | 277.2–727.9 | 2.63× |
| 19 | 1698.9 → 291.6 | 5.83× | 261.7–814.3 | 3.11× | 1623.1 → 404.6 | 4.01× | 330.6–1113.1 | 3.37× |

</details>

So the honest summary is narrower than the original title. On this model
backfill has a large effect, and an extreme job-size weight has an effect of
comparable size, which on some seeds is larger. Neither says anything yet about
a real cluster: the workload is synthetic and every job in it is a whole-node
job.

**Time limits, measured this time.** The current simulator can replace the
generator's padding with exact limits (`--time-limit-model exact`) and change
nothing else. Over seeds 0–9 with conservative backfill, on the same
unreleased version (so the same caveat applies):

| time limits | mean CPU utilisation | mean of per-seed mean wait |
| --- | --- | --- |
| padded (generator default) | 84.2% | 489.1 min |
| exact (limit = runtime) | 86.3% | 656.6 min |

Exact limits raised utilisation on 7 of the 10 seeds and raised mean wait on 9
of 10 (the earlier unreleased state above had utilisation up on 9 of 10). From `schedlab --jobs 300 --seeds 10` with and without
`--time-limit-model exact`. Accurate requests bought throughput and cost
waiting on this workload; they were not the free lever the original post
described. Why was not isolated.

**Slurm is not EASY.** The original post framed EASY backfill (Lifka, 1995),
which protects only the first blocked job's reservation, as what Slurm does.
Slurm's scheduling guide says its backfill scheduler "will start lower priority
jobs if doing so does not delay the expected start time of **any** higher
priority jobs" ([sched_config.html](https://slurm.schedmd.com/sched_config.html),
Slurm 26.05), which is closer to conservative backfill. Version 0.1 of the
simulator modelled only EASY; the next version, not yet released, defaults to a
conservative, per-node, cycle-based model of `sched/backfill` and keeps EASY as
an option. The repository's
[README](https://github.com/Zhanyl-tech/slurm-scheduler-lab) still describes
v0.1 until that version is published.

The project page is [slurm-scheduler-lab](/projects/slurm-scheduler-lab/).

---

## The original post (26 July 2026), with corrections marked

*Text is unchanged except where a correction is marked in brackets.*

I wanted to change `PriorityWeightFairshare` on a cluster and could not justify
the experiment. The feedback loop is days long, the blast radius is everyone's
queue, and the only rollback signal is people complaining in Slack.

So I wrote the thing that lets you try it offline:
[**slurm-scheduler-lab**](https://github.com/Zhanyl-tech/slurm-scheduler-lab).
It implements Slurm's `priority/multifactor` formula and EASY backfill, reads
`PriorityWeight*` straight out of a `slurm.conf`, and replays either a synthetic
workload or a real trace from `sacct`.

Then it kept telling me I was tuning the wrong thing. *[Correction: on one
seed. See above.]*

### First, backfill is doing most of the work

Baseline, 300 jobs on 16 nodes *[synthetic generator, seed 5, simulator v0.1;
reproduce with `schedlab --compare-backfill --jobs 300 --seed 5` on commit
`c02b52f`]*:

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

### Then the weights, which move much less

Sweeping `PriorityWeightJobsize` across four orders of magnitude *[correction:
the sweep is 0, 1,000, 10,000 and 100,000, two orders of magnitude above
zero]*:

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
by about 40%. Backfill moved it by 400%. *[Correction: true for seed 5 only,
which had the smallest sweep effect of seeds 0–19. The median sweep effect was
3.06×, and "100,000x" should read "100× across the non-zero weights".]*

`PriorityWeightFairshare` was flatter still — it redistributes wait *between*
accounts, which is its job, without changing the total much. *[Not re-checked
across seeds.]*

### The number that actually explains the queue

Both runs above report the same line:

```
time-limit accuracy    32.2 %
```

Jobs use about a third of the wall-clock they ask for. That is a property of my
generator, not a measurement — I set the padding to ~3x because that is the
range published trace studies keep reporting. *[Correction: no trace study was
cited, and the padding, max(1.05, N(3, 1)), is the lab's own choice. See the
simulator's README.]* Whether it holds on your cluster is a one-line `sacct`
query, and I'd rather you check than take my word for it.

It matters because **backfill plans against what users request, not what their
jobs need.** The scheduler computes a shadow time — the earliest moment the
blocked job can start, assuming every running job runs to its full limit — and
then only backfills work it can *prove* will not delay that reservation.
*[Slurm's backfill protects every higher-priority job's expected start, not
only one reservation; see above.]*

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
instantly while the other waits for the reservation to clear. *[That holds for
one job and one gap. Across a whole synthetic workload, exact limits raised
mean wait on 9 of 10 seeds; see above.]*

### What I'd do differently

I came in expecting to ship a weights change. What I'd actually do first:

1. **Measure `time-limit accuracy` on the real trace.** One `sacct` query. If
   it's near 30%, that's the finding.
2. **Fix the defaults before the weights.** A partition `DefaultTime` that
   matches reality beats any weight I sweep here. *[Correction: not shown by
   anything in this post.]*
3. **Then tune weights** — for *who waits*, which is what they genuinely
   control, not *how long the queue is*.

The simulator is on
[GitHub](https://github.com/Zhanyl-tech/slurm-scheduler-lab). Point it at your
own `slurm.conf` and `sacct` output *[command updated in September 2026 to the
current CLI, which needs the `Timelimit` column and the node shape]*:

```bash
sacct -a -X --parsable2 --starttime=now-30days \
      --format=JobID,User,Account,Submit,Elapsed,Timelimit,NNodes,ReqCPUS,ReqTRES \
      > trace.txt

schedlab --slurm-conf /etc/slurm/slurm.conf --sacct trace.txt --nodes 64 --cpus 32 --gpus 4
```

I'd genuinely like to know whether the 32% holds up on a production trace, or
whether my synthetic workload is flattering itself.

### Caveats

This is a model, not a controller. Node selection is first-fit with no topology
awareness, backfill reservations are computed on aggregate CPU/GPU counts rather
than per node *[true of v0.1; the current default plans per node]*, fairshare
is flat rather than hierarchical, and there's no preemption or gang scheduling
*[the current version models some preemption; gang time-slicing is still out]*.
Those simplifications are listed in the README because they bound what the
numbers above are allowed to claim: they're good for comparing *policies
against each other* on the same workload, and not for predicting absolute wait
times on your cluster.
