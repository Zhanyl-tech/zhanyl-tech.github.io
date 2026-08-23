---
title: "vLLM vs TensorRT-LLM: Inference Throughput"
date: 2026-01-20
description: "A measured throughput comparison of vLLM and TensorRT-LLM on Llama-3 70B, and why the faster engine is not automatically the right one."
summary: "A measured throughput comparison of vLLM and TensorRT-LLM on Llama-3 70B, and why the faster engine is not automatically the right one."
tags: [vllm, tensorrt-llm, inference, benchmark, llama, gpu, a100]
status: "First pass — measured, single GPU"
weight: 6
ShowToc: false
---

*A first-pass comparison on one A100, not a rigorous study. The limitations
below bound every number here.*

**Setup.** Single NVIDIA A100 80GB SXM · Llama-3 70B (BF16) · vLLM 0.4.1 ·
TensorRT-LLM 0.9.0 · 512 input → 128 output tokens · no quantization, no
speculative decoding.

| batch | vLLM (tok/s) | TensorRT-LLM (tok/s) | delta |
|---|---|---|---|
| 1 | 412 | 487 | +18% |
| 4 | 1,380 | 1,710 | +24% |
| 8 | 2,240 | 2,890 | +29% |
| 16 | 3,180 | 4,210 | +32% |

TensorRT-LLM is consistently faster and the gap widens with batch size, which
is what ahead-of-time compilation and fused kernels are for.

## The result that decided the choice

**The faster engine was not the one worth deploying.** vLLM's PagedAttention
manages KV-cache in pages rather than contiguously, so it admits more
concurrent sessions before it runs out of memory. TensorRT-LLM trades that
flexibility for raw throughput.

For an agentic workload — many concurrent sessions, bursty arrivals, tool-call
round trips — a 30% throughput reduction is recoverable by adding hardware.
**Running out of memory when session 87 spins up is not.** Throughput is the
number everyone quotes and it was not the number that mattered.

## What this does not measure

Stated here rather than at the bottom, because these bound every figure above.

- **Continuous batching.** Real agentic traffic does not arrive in uniform
  batches, and this test does.
- **KV-cache pressure.** The session count at which each engine begins to
  degrade is the interesting threshold, and it is not measured here.
- **Latency percentiles.** Throughput hides p99 variance, which is what a
  user of a tool-calling agent actually feels.
- **Quantization.** INT8 and FP8 on TensorRT-LLM would likely change the
  picture substantially.
- **One GPU, one model, one version pair.** Nothing here generalises to a
  different card, a smaller model, or a later release.

The continuous-batching comparison is the number that would actually settle
this, and it has not been run.

**Write-up:** [vLLM vs TensorRT-LLM: first throughput numbers on Llama-3 70B](/experiments/2026-01-20-vllm-vs-tensorrt-llm-first-look/)
