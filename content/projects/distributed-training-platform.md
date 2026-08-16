---
draft: true  # Retired: the 128-GPU distributed training project was dropped. Kept in git history and marked draft rather than deleted, so it is off the public site without losing the writing.
title: "128-GPU Distributed Training Platform"
date: 2026-01-01
description: "Distributed ML training infrastructure for large-scale models: FSDP, gradient checkpointing, mixed precision, and cost-optimized multi-node orchestration."
tags: [distributed-training, fsdp, pytorch, gpu, hpc, kubernetes, multi-node]
summary: "Building production-grade distributed training infrastructure across 128 GPUs — orchestration, fault tolerance, and cost optimization for large model training."
ShowToc: true
weight: 2
status: "In Progress"
---

**Status:** 🟡 In Progress — Deadline August 2026  
**Stack:** PyTorch FSDP · DDP · Ray · SLURM · Kubernetes · NCCL · Mixed Precision

---

## What This Is

Production distributed training infrastructure for training large-scale ML models across 128 GPUs. Covers the full stack: job orchestration, efficient parallelism strategies, fault tolerance, and cost optimization.

This is the infrastructure that makes it practical to train models that don't fit on a single GPU — or even a single node.

## Problem Statement

Training a 7B parameter model on a single A100 is straightforward. Training a 70B+ model across multiple nodes with:
- Efficient gradient synchronization (minimize communication overhead)
- Fault tolerance (one GPU failure shouldn't kill a 10-hour run)
- Optimal parallelism strategy (when to use FSDP vs DDP vs tensor parallel)
- Cost control (minimize GPU-hours without sacrificing convergence)
- Reproducibility (same seeds, same results, every run)

...requires purpose-built infrastructure. This project builds it.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Job Scheduler Layer                        │
│              SLURM / Ray · Job Queue · Priority               │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                 Distributed Training Layer                    │
├─────────────────┬────────────────────┬────────────────────── ┤
│  FSDP Sharding  │   Gradient Ckpt    │  Mixed Precision       │
│  (param shards  │   (activation      │  (BF16 forward,        │
│  across ranks)  │   recomputation)   │  FP32 optimizer)       │
└─────────────────┴────────────────────┴───────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                  Communication Layer                          │
│           NCCL · AllReduce · AllGather · Ring Topology        │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                  Hardware Layer                               │
│         128x A100 80GB · NVLink · InfiniBand HDR              │
└──────────────────────────────────────────────────────────────┘
```

## Key Technical Decisions

### FSDP vs DDP: When to Use What

The decision isn't obvious and most documentation doesn't explain the tradeoffs clearly:

**Use DDP when:** Model fits in GPU memory with a reasonable batch size. DDP is simpler, faster (no sharding communication overhead), and easier to debug.

**Use FSDP when:** Model doesn't fit in single GPU memory, or you need to scale across many nodes efficiently. FSDP shards parameters, gradients, AND optimizer state — enabling training of models 4-8x larger than DDP allows.

**The grey zone:** 7B-13B models often fit in DDP if you're aggressive about gradient checkpointing and mixed precision. Worth benchmarking before committing to FSDP complexity.

### Gradient Checkpointing Strategy

Naive gradient checkpointing (recompute everything) reduces memory usage by ~60% but increases compute by ~30%. Selective checkpointing (recompute only expensive operations) gets most of the memory savings with less compute overhead.

Implementing an activation memory profiler to identify which layers benefit most from recomputation.

### Fault Tolerance at Scale

At 128 GPUs, hardware failures are a matter of when, not if. Building:
- Async checkpoint saves every N steps (configurable)
- Failure detection with automatic job restart from last checkpoint
- Degraded-mode training (run on N-1 GPUs if one fails, sync optimizer state)

## Benchmarks (Planned)

| Model Size | GPUs | Batch Size | Throughput | GPU Utilization |
|------------|------|------------|------------|-----------------|
| 7B | 8 | 32 | — | — |
| 13B | 16 | 16 | — | — |
| 70B | 128 | 64 | — | — |

## Milestones

- [ ] **M1** (March 2026): 8-GPU baseline — DDP, profiling, observability
- [ ] **M2** (May 2026): FSDP implementation, 16-GPU scaling tests
- [ ] **M3** (July 2026): 128-GPU runs, fault tolerance, cost analysis
- [ ] **M4** (August 2026): Full benchmark suite, architecture writeup, public repo

## Related Posts

*Posts will appear here as they're published.*

---

*[GitHub: Available August 2026](https://github.com/Zhanyl-tech)*
