---
title: "k8s-gpu-scheduler-lab"
date: 2026-08-16
description: "A controlled comparison of Kubernetes GPU schedulers on the same workload traces, built on kwok so it runs without GPUs."
summary: "A controlled comparison of Kubernetes GPU schedulers on the same workload traces, built on kwok so it runs without GPUs."
tags: [kubernetes, gpu, scheduling, kwok, benchmark]
status: "Phase 1 shipped"
repo: "https://github.com/Zhanyl-tech/k8s-gpu-scheduler-lab"
weight: 3
ShowToc: false
---

**[github.com/Zhanyl-tech/k8s-gpu-scheduler-lab](https://github.com/Zhanyl-tech/k8s-gpu-scheduler-lab)** · Python · MIT

*Phase 1 of 3 is public: the kwok substrate, the workload generator, the metrics,
the degenerate baselines, and K0 measured on a real control plane. Kueue,
Volcano, NVIDIA's bin-packing and KAI are not built, and the 34% fragmentation
claim the repo exists to test has not been tested.*

Slurm and Kubernetes solve the same problem — allocating scarce accelerators
across competing jobs — with different mechanisms. Slurm uses multifactor
priority plus EASY backfill. Kubernetes splits it: Kueue does quota and
admission, Volcano does gang scheduling and DRF fairness, NVIDIA KAI does
topology-aware gang scheduling with DRA.

**Nobody has published a controlled comparison on the same trace.** That
comparison is the product.

Built on kwok, so simulated GPU nodes advertise `nvidia.com/gpu` and scheduling
decisions are real while the hardware is not — one command on a laptop, no
cloud account. It carries the same conventions as
[slurm-scheduler-lab](/projects/slurm-scheduler-lab/) and
[slurm-rca-bench](/projects/slurm-rca-bench/): the same trace format, the same
metrics vocabulary, and degenerate baselines (FIFO, random, largest-first) in
every results table.

What kwok **cannot** tell you is stated above the results, not in a footnote:
it simulates scheduling, not execution, so NCCL performance, real GPU
contention, thermal behaviour and network topology effects are all outside what
any number here can claim.
