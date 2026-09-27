---
title: "slurm-rca-bench"
date: 2026-08-01
lastmod: 2026-09-27
description: "An incident-diagnosis benchmark for the Slurm control plane: 10 scenarios (6 runnable, 2 causal chains measured on a Docker test cluster), closed-vocabulary scoring, and degenerate baselines. No agent scored yet."
summary: "An incident-diagnosis benchmark for the Slurm control plane: 10 scenarios, 6 runnable, 2 causal chains measured, degenerate baselines. No agent scored yet."
tags: [slurm, benchmark, root-cause-analysis, llm-agents]
status: "Phase 2 of 6 · 6 of 10 scenarios runnable · leaderboard empty"
stage: "partial"
repo: "https://github.com/Zhanyl-tech/slurm-rca-bench"
weight: 7
ShowToc: true
---

**[github.com/Zhanyl-tech/slurm-rca-bench](https://github.com/Zhanyl-tech/slurm-rca-bench)** · Python · MIT

<p class="project-status"><span class="status status-partial">partial</span>
Ten scenarios designed: six runnable, four blocked. Two causal chains (S01,
S06) were measured on a CPU-only Docker Compose cluster with one worker (Slurm
25.11.4, faults emulated): S01 in one fully probed run plus a second run that
confirmed its queue-depth signal, S06 in one run. The rest are designed, not
observed. The September 2026 injection fixes have not been re-run on that
cluster. No agent has been scored.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26 (0.2.0: S01 rescored, four scenarios blocked). Merge or push it
before publishing; `slurm-rca list` and `slurm-rca baselines` below were run on
that branch. -->

The published root-cause-analysis benchmarks for LLM agents that I know of
mostly target software services: [OpenRCA](https://github.com/microsoft/OpenRCA)
(telemetry from telecom, bank and market systems) and
[ORCA-bench](https://arxiv.org/abs/2607.28545) (on-call incidents). The closest
to HPC are an LLM-agent diagnosis system for AI clusters that came with its own
benchmark ([arXiv:2411.05349](https://arxiv.org/abs/2411.05349), November
2024) and [AOBench](https://github.com/MSKazemi/aobench), agents operating HPC
systems through mock Slurm tools (whether it includes graded root-cause tasks
was not established). A search in September 2026 found no public benchmark
that grades Slurm control-plane incidents on a live emulated cluster against a
closed vocabulary; a search is not proof, so this is not a claim to be first.

## The thesis

Scores are poor but improving. On ORCA-bench (July 2026, 884 incident tasks)
the best strict RCA accuracy is 30.6% and the best partial-credit "RCA depth"
48.8% ([arXiv:2607.28545](https://arxiv.org/abs/2607.28545)). Cloud dependency
graphs are large, change between deploys, and are rarely written down, so an
agent has to infer the system's shape and diagnose the fault at once. A Slurm
control plane is small, documented and changes only when redeployed. The
hypothesis — that some of what agents lose is lost to graph inference, not
reasoning — is what [cluster-sre-agent](/projects/cluster-sre-agent/) is built
to test.

## The first finding was about the benchmark itself

The flagship scenario was built around the model everyone repeats: a storage
stall backs up through the accounting path until the controller's queues fill
and scheduling halts, about thirteen minutes later.

Then I measured it. With the database container frozen for about fifteen
minutes, `sacct` blocked with no error, the controller's DBD agent queue grew
slowly, and jobs submitted *during* the stall still started and completed.
Scheduling degraded (job starts slowed to tens of seconds) and did not halt.
That timeline is from one fully probed run on the emulated cluster above; a
second run confirmed the queue growth (depth 6 at three minutes rather than
fourteen; the scenario's caveats tie the growth to accounting traffic, not
elapsed time).

A second storage failure, `StateSaveLocation` unwritable, failed loudly instead:
the one submission attempted during the fault was rejected at once with an I/O
error, and no backlog built up (one run). Whether a *stalled* state-save
filesystem would block the controller is untested.

## The second finding: the flagship still credited a layer that was not there

The first correction kept "a stalled shared filesystem beneath the database" as
S01's full-credit answer. An audit in September 2026 pointed out that the
emulated cluster has no shared filesystem: the injection freezes the database
itself, so a faithful agent could only ever find the database, and would have
been marked down for it. S01 now gives full credit to `db.mysql` and zero to
the storage layer, under a new id.

## Baselines are the number to ask for first

A score of 0.52 means nothing if answering the same component to every task
scores 0.50. The suite computes that floor from the ground truth alone:

```
$ slurm-rca baselines          # run on 2026-09-27

  degenerate baselines over 6 runnable scenarios

   depth   brier  strategy
   0.333   0.222  always-db.mysql               <- floor
   0.208   0.139  always-abstain
   0.200   0.139  always-slurm.slurmctld
   0.167   0.139  always-gpu.device
   0.167   0.139  always-storage.state_save
   0.101       —  uniform-random
   0.067   0.000  always-slurm.slurmdbd
   0.067   0.000  always-storage.shared_fs

  DEGENERATE: always-db.mysql 0.333 (threshold 0.25).
```

`depth` is the partial-credit score; `brier` is the best calibration score each
constant answer can reach (Brier has a trivial floor of its own, so it is only
read next to depth).

**The runnable suite is degenerate right now, and says so.** Two of the six
runnable scenarios have the database as their root cause, so answering
`db.mysql` to everything clears the 0.25 threshold a test enforces. History:
at five scenarios that constant answer scored 0.290; adding scenarios whose
causes lie elsewhere cut it to 0.145 over ten; the two corrections above (S01's
credit moving to the database, and four scenarios blocked out of the
denominator) pushed it back up. The fix is more runnable scenarios with causes
elsewhere, never retuned weights.

## Scoring

Answers are node identifiers from a closed vocabulary, not free text, so
grading is a dictionary lookup rather than an LLM judge grading LLM agents.
Partial credit never rises from cause to consequence along the chain, and two
scenarios are deliberately **undiagnosable**: abstaining scores full marks, and
naming any plausible cause scores zero, including the one a human would pick.
Without them a benchmark rewards fluent overconfidence.

```
$ slurm-rca list

  10 scenarios · 6 runnable · 4 blocked · 2 multi-layer · 2 undiagnosable
```

## Limitations

- **Faults are emulated** (a paused database container, a synthetic
  `nvidia-smi`), and there are no real GPUs.
- **Four of ten scenarios are blocked**: their injections cannot produce their
  ground truth on this cluster (one was measured not to work at all).
- **Ten scenarios is not enough to rank models**; phase 3 targets 15–20.
- **One Slurm version (25.11.4), one engineer's judgement** on the credit
  weights, each with a written rationale.
