---
title: "Projects"
description: "Open-source infrastructure tooling. Each links to its repository; each has a runnable demo or a reproducible benchmark."
---

## Measurement & benchmarks

**[slurm-rca-bench](https://github.com/Zhanyl-tech/slurm-rca-bench)** — the
first public incident-diagnosis benchmark for HPC schedulers. Ten reproducible
failure scenarios across six fault families, two of them deliberately
*undiagnosable* so that confident guessing is penalised rather than rewarded.
Answers are scored with partial credit against degenerate baselines, so a
number means something: an agent that answers `db.mysql` to every question and
reads no telemetry scores 0.145, and anything that fails to clear the floor has
demonstrated fluency rather than diagnosis. Its first finding was about itself
— the flagship scenario, built around the widely-repeated model that a storage
stall backs up through the accounting path until scheduling halts, does not
happen. Measured on a live cluster, scheduling continued throughout.

**[slurm-scheduler-lab](https://github.com/Zhanyl-tech/slurm-scheduler-lab)** —
replays real Slurm job traces against multifactor priority and EASY backfill, a
discrete-event simulator for testing scheduling policy before it reaches a
production controller. Reads `PriorityWeight*` straight from a `slurm.conf` and
replays `sacct` output. The measured result: enabling backfill moved CPU
utilisation from 72.2% to 83.6% and mean wait from 1,913 to 374 minutes, while
sweeping the priority weights barely moved either. The real lever was users'
`--time` limits.

Write-up: [Your Slurm priority weights matter less than your users' time
limits](/experiments/2026-07-26-slurm-backfill-time-limits/)

**k8s-gpu-scheduler-lab** — *in progress.* A controlled comparison of
Kubernetes GPU schedulers (Kueue, Volcano, NVIDIA KAI) on the same workload
traces, built on kwok so it runs on a laptop with no GPUs. Nobody has published
one. Goes public when the baseline is real.

## Cluster tooling

**[gpu-reaper](https://github.com/Zhanyl-tech/gpu-reaper)** — detects and
reclaims wasted GPU allocations on Slurm clusters, with guardrails that fail
safe when telemetry is stale. Observe-by-default; a gap in the samples is
treated as a collector fault rather than an idle GPU, so a monitoring outage
can never cancel the cluster; and a kill requires a history of prior warnings.

**[ib-slurm-exporter](https://github.com/Zhanyl-tech/ib-slurm-exporter)** —
correlates InfiniBand/RoCE fabric counters with the Slurm job that owns them,
for diagnosing multi-node training slowdowns. Refuses to attribute a device two
jobs share rather than guessing.

**[epilog-gpu-validator](https://github.com/Zhanyl-tech/epilog-gpu-validator)**
— node-level GPU validation in the Slurm epilog path, catching degraded devices
before the next job lands on them. Slurm drains a node when the epilog exits
non-zero, so the tool distinguishes persistent faults from transient ones and
never drains on ignorance: a failed query exits clean.

**[slinky-gitops](https://github.com/Zhanyl-tech/slinky-gitops)** — Slurm on
Kubernetes via Slinky (SchedMD/NVIDIA), with auth-key rotation and GitOps
continuous sync. Documents honestly what does and does not work on the current
release, including that the rotation does not propagate.

## Agents

**[cluster-sre-agent](https://github.com/Zhanyl-tech/cluster-sre-agent)** —
*design published, agent in build.* Multi-agent diagnosis over an explicit
cluster dependency graph, built as five ablatable configurations specified
before any results existed, scored on slurm-rca-bench. The dependency graph and
the read-only tool surface are built and tested; the LLM configurations are
not, so no diagnosis accuracy has been measured yet.

## Research infrastructure

**[research-platform](https://github.com/Zhanyl-tech/research-platform)** —
point-in-time data semantics for quantitative research: as-of queries, feature
lineage, and leakage detection. Every record carries the date it became
*knowable* separately from the date it describes, which makes an entire class
of backtest bug structurally impossible rather than carefully avoided.
