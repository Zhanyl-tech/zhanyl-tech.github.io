---
title: "k8s-gpu-scheduler-lab"
date: 2026-08-16
lastmod: 2026-09-27
description: "A controlled comparison of Kubernetes GPU schedulers on identical traces, on a real control plane with simulated GPU nodes. K0 and four degenerate baselines are built; Kueue, Volcano and KAI are planned."
summary: "A controlled comparison of Kubernetes GPU schedulers on identical traces, on a real control plane with simulated GPU nodes. K0 and the degenerate baselines are built; Kueue, Volcano and KAI are planned."
tags: [kubernetes, gpu, scheduling, kwok, benchmark]
status: "Phase 2 of 3 in progress · Kueue, Volcano, KAI not built"
stage: "partial"
repo: "https://github.com/Zhanyl-tech/k8s-gpu-scheduler-lab"
weight: 1
ShowToc: true
---

**[github.com/Zhanyl-tech/k8s-gpu-scheduler-lab](https://github.com/Zhanyl-tech/k8s-gpu-scheduler-lab)** · Python · MIT

<p class="project-status"><span class="status status-partial">partial</span>
Built: the kind + kwok substrate, the workload generator, the metrics, K0 (the
default <code>kube-scheduler</code>) and four degenerate baselines, and the
Phase 2 measurement harness. <strong>No cluster run has been made with the
Phase 2 harness</strong>, so every cluster number is Phase 1's, from single
runs of K0, D-fifo, D-random and D-largest; D-preempt, added in Phase 2, has
run only in the in-process model. Not built: Kueue, Volcano, NVIDIA's Volcano bin-packing and KAI with DRA,
which are the comparison itself.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26 (Phase 2 harness). Merge or push it before publishing. -->

Slurm and Kubernetes solve the same problem, allocating scarce accelerators
across competing jobs, with different machinery. Slurm uses one controller:
multifactor priority plus backfill. Kubernetes splits it across projects:
Kueue does quota and admission, Volcano gang scheduling and DRF fairness,
NVIDIA's KAI topology-aware gang scheduling with DRA. Each is usually
benchmarked, when at all, against the default scheduler on a workload of its
own choosing.

This lab runs them on **the same trace and the same fleet**. I have not found a
published controlled comparison of the Kubernetes options on an identical trace
and substrate. The closest I found is
[Radiant's comparison of Kueue, Volcano and Slinky](https://radiant.co/blog/benchmarking-kueue-volcano-and-slinky-on-radiant)
(2026-04-23), which used the same mock jobs but different hardware for Kueue
(2× H200) than for the other two (2× H100). What this lab adds is the control:
one trace, one fleet, stated metric definitions, and degenerate baselines in
every table.

## What kwok can and cannot tell you

Every GPU node is a [kwok](https://kwok.sigs.k8s.io/) node: an API object with
no kubelet behind it, advertising `nvidia.com/gpu` it does not have. The
control plane is real, the scheduler is real, and every binding decision is
real. Nothing else is. So the lab can measure placement, queue wait, admission
order, packing, fragmentation and gang behaviour, and it **cannot** measure
NCCL performance, real GPU contention, MIG/MPS sharing, thermal behaviour, or
whether a topology-aware placement was actually faster. A scheduler that wins
here has made better *decisions* on this trace; it has not been shown to make
jobs faster.

## The claim it was started to test

NVIDIA reported that adding bin-packing to the Volcano scheduler reduced GPU
fragmentation on one production cluster. The primary source is NVIDIA's
technical blog,
[*Practical Tips for Preventing GPU Fragmentation for Volcano Scheduler*](https://developer.nvidia.com/blog/practical-tips-for-preventing-gpu-fragmentation-for-volcano-scheduler/)
(Ameya Parab, 2025-03-31). On a DGX Cloud Kubernetes cluster of four-GPU L40S
nodes, compared with Volcano's default gang placement, it reports nodes with all
four GPUs free going from **18 to 214** and average GPU utilisation of roughly
90%. It gives no node count, no workload, and no percentage reduction in
fragmentation.

The figure this repo was started with, "a **34%** reduction versus the default
scheduler, shared at KubeCon EU 2026", is **unverified** in both value and
attribution. The only place I found it is a third-party blog post
([Gheware, 2026-05-13](https://devops.gheware.com/blog/posts/top-kubernetes-integrations-ai-gpu-acceleration-2026.html)),
which credits "benchmarks shared at KubeCon EU 2026" and names no talk,
speaker, slides or recording. NVIDIA's post does not mention KubeCon or give
any percentage, and the lab has not tested the figure. (Both pages re-read
2026-09-27.) The quantity NVIDIA did report, how nodes are distributed by
free-GPU count, is computable from the samples the lab records; the metric is
not implemented yet.

## Its most useful finding so far is about a metric

Fragmentation is reported under three definitions because they disagree. Under
the queue-relative definition (A), the largest-first baseline read **0.0%**,
which sounds like perfect packing; under a fixed reference request (B) the same
run read **55.6%** (Phase 1, kind + kwok control plane, one run). Largest-first
starves small jobs, so a one-GPU pod is always pending and no free GPU ever
counts as unusable under A. A fragmentation number that does not state its
definition cannot be reproduced or disputed, and that includes the 34% above.
A third, structural definition (C) is shared with
[slurm-scheduler-lab](/projects/slurm-scheduler-lab/) through a common golden
test vector, so the Slurm and Kubernetes sides compute it identically.

## Configurations

| id | scheduler | status |
| --- | --- | --- |
| K0 | default `kube-scheduler` + device plugin | <span class="status status-built">built</span> |
| D-fifo, D-random, D-largest, D-preempt | degenerate baselines: a scheduler that does not clearly beat D-random has not been shown to schedule | <span class="status status-built">built</span> |
| K1 | + Kueue (quota, admission) | <span class="status status-planned">planned</span> |
| K2 | + Volcano (gang, DRF) | <span class="status status-planned">planned</span> |
| K3 | + NVIDIA's Volcano bin-packing | <span class="status status-planned">planned</span> |
| K4 | NVIDIA KAI + DRA | <span class="status status-planned">planned</span> |
| S0 | Slurm on the same trace, via slurm-scheduler-lab | <span class="status status-partial">partial</span> (model side built there) |

## Phase 2: fixing how numbers are produced

Phase 1's results showed the harness, not the schedulers, was the largest
source of variation: the same K0 configuration on the same trace and seed gave
very different utilisation on two runs, because API latency fed back into the
simulated clock, and the baselines were bound by a loop with no queue at all
while K0 had kube-scheduler's backoff. Phase 2 adds, and tests without a
cluster:

- repeated, interleaved runs reported as mean ± sd with a stability verdict,
  and a seeded bootstrap screen for differences (with its false-alarm rate
  measured rather than assumed);
- the baselines bound through a reproduction of kube-scheduler's queue
  (activeQ, backoff, unschedulable pool), so both sides go through the same
  mechanics;
- kube-scheduler's backoff scaled to the replay speed-up, with the residual
  recorded;
- a preemption baseline, a startup-delay knob, topology scenarios, and
  stranded gang GPU-hours in place of a thresholded "deadlock rate".

Whether five repeats tame the spread on a real control plane is unknown until
it runs.

```bash
make up        # kind + kwok + the simulated fleet
make bench     # every built configuration, REPEAT=5 times each
make bench-model   # the degenerate baselines in an in-process model; rows labelled "model", never compared with cluster rows
```
