---
title: "GPU Reaper"
date: 2026-07-26
lastmod: 2026-09-27
description: "Find wasted GPU allocations on a Slurm cluster and, only if enabled, drain and cancel them, with guardrails that refuse to act on missing, stale or unreadable telemetry."
summary: "Find wasted GPU allocations on a Slurm cluster and, only if enabled, drain and cancel them; it refuses to act on missing, stale or unreadable telemetry."
tags: [slurm, gpu, nvidia, dcgm, prometheus, golang]
status: "Simulated telemetry only · not run on a cluster"
stage: "built"
repo: "https://github.com/Zhanyl-tech/gpu-reaper"
weight: 5
ShowToc: true
---

**[github.com/Zhanyl-tech/gpu-reaper](https://github.com/Zhanyl-tech/gpu-reaper)** · Go · MIT

<p class="project-status"><span class="status status-built">built</span>
Exercised against a GPU simulator, a fake <code>squeue</code>, fake
<code>nvidia-smi</code>, fake <code>scancel</code>/<code>scontrol</code> and
synthetic dcgm-exporter pages. <strong>Nothing has been run against a real
Slurm controller or a real GPU.</strong> Observe mode is the default.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26 (DCGM source, stricter escalation ladder). Merge or push it before
publishing. -->

```
make demo
```

No cluster, no GPUs, no risk: a fake `squeue` on `PATH`, simulated telemetry,
observe mode. Two jobs are classified `hung`; each is alerted once its
evidence window is covered, then escalated to a dry-run drain. Nothing is
cancelled. (`make demo-check` asserts exactly that; its check script passed
on 2026-09-27.)

## The problem

*An illustrative example, not a measurement.* A researcher requests 16 H100s
for 48 hours. Four hours in, the training script deadlocks on an all-reduce
because one rank died. The allocation is still held, and Slurm is content: the
job is `RUNNING`, the nodes are busy, the queue is moving. That is 16 GPUs × 44
hours, **704 GPU-hours**, of a contended resource doing nothing.

Slurm can record per-job GPU utilisation, but it does not act on it.

![Scheduler and telemetry feed a policy engine that emits a finding, then a four-step escalation ladder gated by mode](/images/diagrams/gpu-reaper-escalation.svg)

## Why it will not kill your job

Killing a healthy job is much worse than letting a wasted one run another hour.
Every default follows from that asymmetry, and each guard is pinned by named
tests in the README:

- **Observe by default, twice over.** Observe mode wires a controller that
  cannot touch the cluster, and the actor refuses to call any controller unless
  enforcing; a mistake in either alone cancels nothing.
- **Warmup and a covered window.** Young jobs are not judged, and their warmup
  samples are discarded. A breach is confirmed only when, on every node the job
  holds, the evidence spans the window (less one allowed gap), holds a minimum
  number of observations, and every sample breaches. One snapshot is never a
  sustained breach.
- **Peak, not mean.** One busy sample on any GPU in the window means alive.
- **Gaps, staleness and outages reset the clock** — and the escalation
  history. A hole between observations longer than `max_sample_gap` (with the
  defaults, any failed collection cycle) is a collector fault, not idleness,
  and the ladder starts again from Alert. This is the guard that keeps a
  monitoring outage from being read as idle GPUs.
- **Unreadable is unknown, never idle.** `[N/A]` and error values are not 0; a
  GPU with unreadable utilisation, or in MIG mode, stops its job being judged.
- **Signature gating.** `starved` and `unknown` never pass Alert, and `hung`
  stops at Drain unless you allow more, because a long checkpoint write looks
  the same as a deadlock.
- **The ladder.** Drain needs an earlier Alert; Cancel needs a drain that was
  executed and confirmed at least a window earlier, and the reason is written to
  the job's AdminComment first.

| Signature | Evidence | Ceiling by default |
| --- | --- | --- |
| `idle` | no memory held; no processes; idle power draw | `cancel`, only if a cancel stage is configured |
| `hung` | memory held; processes seen; zero compute | `drain` |
| `starved` | memory held; low but non-zero compute | `alert` |
| `unknown` | breaching, but no signature matches (including missing process or power data) | `alert` |

## Telemetry sources

- **`nvidia-smi`, per node** — the full signature set.
- **dcgm-exporter** (new, **unverified**) — written against dcgm-exporter's
  source and tested only on synthetic pages. dcgm-exporter exposes no
  per-process data, so DCGM-backed findings can never be `idle` or `hung` and
  never pass Alert. A central DCGM source is what lets a single daemon judge
  multi-node jobs; a per-node daemon skips them by design.

## Limitations

- **Not run on real hardware or a real cluster.**
- **Shared-node attribution.** GPU samples identify a node, not a job, so jobs
  on a node that hosts several GPU jobs are skipped and counted rather than
  guessed at. Correct attribution means mapping GPU PIDs to jobs through the
  Slurm cgroup tree, and on Slurm 26.05 that tree is keyed by SLUID, not job
  ID ([upgrade notes](/experiments/2026-07-26-slurm-25-11-upgrade-notes/)).
- **Utilisation is coarse.** A kernel occupying one SM can report the same
  utilisation as a saturated device, which is why high utilisation is never
  treated as proof of health, only low utilisation as evidence of a problem.
- **Drain is never undone** by the tool; a person resumes the node.
- **NVIDIA only; MIG is not judged.**

## The set

One of three fleet tools with one rule, **never act on absent evidence**:
[epilog-gpu-validator](/projects/epilog-gpu-validator/) checks hardware between
jobs and exits clean when it cannot see it, and
[ib-slurm-exporter](/projects/ib-slurm-exporter/) refuses to attribute a port it
can see is shared.
