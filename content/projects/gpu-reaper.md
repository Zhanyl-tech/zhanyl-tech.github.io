---
title: "GPU Reaper"
date: 2026-07-26
description: "Find wasted GPU allocations on a Slurm cluster and escalate them through alert, drain, and cancel."
summary: "Find wasted GPU allocations on a Slurm cluster and escalate them through alert, drain, and cancel."
tags: [slurm, hpc, gpu, nvidia, prometheus, golang]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/gpu-reaper"
weight: 4
ShowToc: false
---

**[github.com/Zhanyl-tech/gpu-reaper](https://github.com/Zhanyl-tech/gpu-reaper)** · Go · MIT

```
make demo
```

No cluster, no GPUs, no risk — fake `squeue`, simulated telemetry, observe mode.
Two jobs get classified as `hung` and escalate from alert to drain in about
thirty seconds.

## The problem

A researcher requests 16 H100s for 48 hours. Four hours in, the training script
deadlocks on an all-reduce because one rank died. The allocation is still held.
Slurm is content: the job is `RUNNING`, the nodes are busy, the queue is moving.

Slurm does not look at GPUs. It looks at allocations. That gap is 16 GPUs ×
44 hours — **704 GPU-hours** of a contended resource, consumed by a process
doing nothing.

## Why it will not kill your job

The whole design follows from an asymmetry: killing a healthy job is far worse
than letting a wasted one run another hour. A researcher whose 40-hour run dies
at hour 39 loses the run *and* their trust in the tool.

So: observe mode is the default, enforcement is opt-in, and escalation requires
sustained evidence. Concretely —

- Jobs younger than the warmup are never judged. Container pulls and dataset
  staging legitimately show zero utilization.
- A breach must hold across the entire window. **One busy sample clears the
  finding**, because evaluation is on peak, not mean.
- A hole in the samples is treated as a collector fault, not idleness. This is
  the guard that stops a monitoring outage from cancelling the whole cluster.
- Cancel requires a previous cycle to have alerted *and* drained. No config
  change can jump a job straight to termination.

## Signatures

Low utilization has several causes, and they deserve different responses.

| Signature | Evidence | Meaning | Ceiling |
| --- | --- | --- | --- |
| `idle` | No memory, no processes, idle power | Allocation is empty | `cancel` |
| `hung` | Memory held, processes resident, zero compute | Deadlocked collective | `cancel` |
| `starved` | Memory held, low but nonzero compute | Dataloader bottleneck | `alert` |
| `unknown` | Breaching, no match | Not modelled | `alert` |

Starvation caps at `alert` deliberately. A slow dataloader is a tuning problem,
and cancelling someone's run over one is how a tool gets uninstalled.

## What building it taught me

Two bugs worth recording, both found by CI rather than by me:

**`.gitignore` matches at any depth.** A bare `bin/` silently excluded
`demo/bin/`, so the fake `squeue` the demo depends on never left my laptop. The
demo the README promised could not have worked for anyone who cloned it. The
fix is anchoring — `/bin/`.

**`$(PWD)` is not guaranteed in make.** It comes from the environment; on the
CI runner it expanded to empty and the demo's `PATH` prepend silently did
nothing. `$(CURDIR)` is make-native and always set.

Neither is exotic. Both were invisible locally and obvious the moment something
other than my machine ran the code — which is the argument for having the demo
itself be a CI job.

## Limitations

GPU samples identify a node, not a job. Where a node hosts several GPU jobs,
attribution is ambiguous and the reaper skips them rather than guess — a false
alert on a healthy job costs more than a missed finding costs GPU-hours. Correct
attribution needs the Slurm cgroup hierarchy to map GPU PIDs back to job IDs,
which is the subject of the next tool.

It reads `nvidia-smi` rather than DCGM, so utilization is coarse: a kernel
occupying one SM reports the same 100% as a saturated device. That is exactly
why high utilization is never treated as proof of health — only low utilization
as evidence of a problem.
