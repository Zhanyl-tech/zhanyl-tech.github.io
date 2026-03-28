---
title: "vLLM vs TensorRT-LLM: First Throughput Numbers on Llama-3 70B"
date: 2026-01-20
description: "Quick benchmark comparing vLLM and TensorRT-LLM throughput on a single A100 80GB with Llama-3 70B. Setup notes, raw numbers, and what I'd investigate next."
tags: [vllm, tensorrt-llm, inference, benchmark, llama, gpu, a100]
summary: "Quick benchmark comparing vLLM and TensorRT-LLM throughput on a single A100 80GB with Llama-3 70B."
ShowToc: false
draft: false
---

Running inference benchmarks as part of the Agentic ML Inference Infrastructure project. This is a first-pass comparison — not a rigorous study, just enough to establish a baseline and understand what to optimize next.

## Setup

- **Hardware:** Single NVIDIA A100 80GB SXM
- **Model:** Llama-3 70B (BF16)
- **Framework versions:** vLLM 0.4.1, TensorRT-LLM 0.9.0
- **Workload:** 512 input tokens → 128 output tokens, batch sizes 1 / 4 / 8 / 16

No quantization, no speculative decoding — baseline comparison first.

## Raw Numbers

| Batch Size | vLLM (tok/s) | TensorRT-LLM (tok/s) | Delta |
|------------|-------------|----------------------|-------|
| 1          | 412         | 487                  | +18%  |
| 4          | 1,380       | 1,710                | +24%  |
| 8          | 2,240       | 2,890                | +29%  |
| 16         | 3,180       | 4,210                | +32%  |

TensorRT-LLM is consistently faster, with the gap widening at higher batch sizes. Expected — TensorRT's AOT compilation and fused kernels are doing real work here.

## What's Actually Happening

vLLM's PagedAttention is doing smart memory management (KV-cache paging), which is why it can handle more concurrent sessions before OOM. TensorRT-LLM trades that flexibility for raw throughput via compiled CUDA kernels.

For my use case (agentic infrastructure with many concurrent sessions), the vLLM memory management model may actually be worth the throughput hit. A 30% throughput reduction is recoverable. Running out of memory when session 87 spins up is not.

## What's Missing From This Benchmark

- **Continuous batching behavior:** How does each handle the arrival pattern of real agentic workloads? Not uniform batch sizes.
- **KV-cache pressure:** At what session count does each start degrading?
- **Latency percentiles:** Throughput numbers hide p99 latency variance, which matters for tool call round-trips.
- **Quantized comparison:** INT8 and FP8 on TensorRT-LLM likely closes the gap with vLLM significantly.

## Next Steps

Running the continuous batching test next week. That's the number that actually matters for the agentic use case.

---

*Part of the [Agentic ML Inference Infrastructure](/projects/agentic-ml-inference-infrastructure/) project.*
