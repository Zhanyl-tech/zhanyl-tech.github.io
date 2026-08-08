---
title: "Epilog GPU Validator"
date: 2026-07-26
description: "Drain a node for a persistently faulty GPU — and never for a transient one."
summary: "Drain a node for a persistently faulty GPU — and never for a transient one."
tags: [slurm, gpu, nvidia, hpc, golang]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/epilog-gpu-validator"
weight: 1
ShowToc: false
---

**[github.com/Zhanyl-tech/epilog-gpu-validator](https://github.com/Zhanyl-tech/epilog-gpu-validator)** · Go · MIT

```
make scenarios
```

Every fault case against a synthetic GPU. No NVIDIA hardware required.

```
SCENARIO        SEVERITY  DRAIN  EXIT
healthy         ok        no     0
remap-pending   transient no     0
thermal         transient no     0
pcie-degraded   degraded  yes    1
hw-slowdown     degraded  yes    1
ecc             fatal     yes    1
remap-failure   fatal     yes    1
missing         n/a       no     0    ← query failed, safe no-op
```

## The problem

A GPU develops a fault mid-job. The job fails, or worse, silently returns wrong
numbers. Slurm marks the node idle. The next job lands on the same card and
fails the same way. Then the next.

Nothing in Slurm looks at GPU health between jobs. Epilog is the hook that
could — it runs on every completion, on the node, as root, while nothing else is
touching the hardware.

![Decision tree: a failed GPU query exits zero and keeps the node in service, while persistent hardware faults exit non-zero and drain](/images/diagrams/epilog-severity.svg)

## Why it's a dangerous tool to write

**Slurm drains the node when Epilog exits non-zero.**

A false positive doesn't produce a bad metric. It removes a working node. And if
the cause is fleet-wide — a driver bug, a monitoring gap, a heatwave — it
removes *every* node, one job completion at a time, faster than anyone can
react.

Two rules follow, and everything else is detail.

**Never drain on ignorance.** If `nvidia-smi` is missing, times out, or returns
something unparseable, that's a *monitoring* failure. Draining on it converts a
broken health check into a cluster-wide outage. That's the `missing` row above,
and it's the most important line in the test suite.

**Separate persistent faults from transient conditions.** A card
thermal-throttling on a hot afternoon is the hardware protecting itself —
draining for it means draining the row every time the CRAC unit hiccups. A card
running **x8 on an x16 slot** is a different animal: it passes every functional
test, halves host-to-device bandwidth, and poisons every collective it joins.
Nobody notices for months.

The distinction I found most worth labouring is volatile versus aggregate ECC.
Uncorrectable errors *since boot* mean the card is failing right now — the job
that just finished may have produced wrong numbers. *Lifetime* errors on a card
that's been clean since its last reset justify nothing.

## Only the job's own GPUs

On a shared node, checking everything means a neighbour's faulty card drains the
node for a job that never touched it. It reads `SLURM_JOB_GPUS` and checks only
those — and if that set can't be determined, it checks nothing and exits 0.

Worth knowing: depending on Slurm version and `GresTypes`, those variables can
contain UUIDs rather than ordinals. Those are skipped rather than guessed at.

## What's deliberately missing

**No `dcgmproftester`.** An active memory-bandwidth test would catch faults that
only appear under load, and the original plan called for one. But it takes tens
of seconds and Epilog doesn't have that budget — if Slurm kills the check
mid-run, the node can be marked down for a check that never reached a
conclusion. That's the opposite of the point. A periodic drain-and-test job is
the right home for it.

Also no XID scraping (needs privileges Epilog doesn't reliably have), no MIG
awareness, and it never un-drains — bringing a node back is a human decision.

## The set

This is the fourth of four. Together they cover the lifecycle of a GPU
allocation: [gpu-reaper](/projects/gpu-reaper/) catches waste while a job runs,
[ib-slurm-exporter](/projects/ib-slurm-exporter/) attributes fabric problems to
the job causing them, this validates the hardware between jobs, and
[slinky-gitops](/projects/slinky-gitops/) runs the whole thing on Kubernetes.

The same principle runs through all four: **never act on absent evidence.**
gpu-reaper treats a sampling gap as a collector fault rather than idleness.
ib-slurm-exporter refuses to attribute a shared device. This exits clean when it
can't see the hardware. In every case the failure mode of guessing is worse than
the cost of not knowing.
