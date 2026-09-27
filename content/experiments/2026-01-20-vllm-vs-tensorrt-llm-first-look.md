---
draft: true  # Withdrawn 2026-09-26: numbers not physically plausible, no artefact. See the comment at the top of the body and /corrections/.
title: "vLLM vs TensorRT-LLM: First Throughput Numbers on Llama-3 70B"
date: 2026-01-20
description: "WITHDRAWN. A throughput comparison on a single A100 80GB whose setup cannot run as stated and whose numbers have no artefact."
tags: [vllm, tensorrt-llm, inference, benchmark]
summary: "WITHDRAWN. A throughput comparison whose setup cannot run as stated."
ShowToc: false
---

<!--
WITHDRAWN on 2026-09-26. draft: true keeps this note off the public site; it is
kept in the repository, not deleted, as the record of what was published. The
public note is on /corrections/.

Why (checked on 2026-09-26):
- Llama-3-70B is 70,553,706,496 parameters (Hugging Face API,
  meta-llama/Meta-Llama-3-70B), about 141.1 GB in BF16. The stated hardware is
  one A100 80GB with no quantization, so the model does not fit.
- Batch-1 decode reads every weight per token: 141.1 GB / 2,039 GB/s (NVIDIA
  A100 80GB SXM spec) = 69.2 ms/token, a ceiling of about 14.4 tok/s. The
  table claims 412 and 487 tok/s at batch 1, 28.5x and 33.7x that ceiling.
- "TensorRT-LLM trades that flexibility for raw throughput" is false for the
  version named: the TensorRT-LLM v0.9.0 README lists "Paged KV Cache for the
  Attention" and "In-flight Batching".
- No scripts, logs or hardware inventory exist. The note is dated 2026-01-20
  and was first committed on 2026-03-28 (ac8c811).
- It promised "the continuous batching test next week"; that test was never
  run.

To republish, see the evidence list in the comment at the top of
content/projects/inference-throughput-benchmark.md: public scripts with pinned
versions, a configuration that fits the hardware, raw per-request logs with a
committed analysis script and repeats, a concurrency/p99-at-KV-budget
workload, and a printed bandwidth-ceiling sanity check.
-->

*Withdrawn. See [corrections](/corrections/).*

## Setup as originally stated

- **Hardware:** Single NVIDIA A100 80GB SXM
- **Model:** Llama-3 70B (BF16)
- **Framework versions:** vLLM 0.4.1, TensorRT-LLM 0.9.0
- **Workload:** 512 input tokens → 128 output tokens, batch sizes 1 / 4 / 8 / 16

This configuration does not fit in 80 GB of GPU memory; see the comment at the
top of this file.

## Numbers as originally published (withdrawn, no artefact)

| Batch Size | vLLM (tok/s) | TensorRT-LLM (tok/s) | Delta |
|------------|-------------|----------------------|-------|
| 1          | 412         | 487                  | +18%  |
| 4          | 1,380       | 1,710                | +24%  |
| 8          | 2,240       | 2,890                | +29%  |
| 16         | 3,180       | 4,210                | +32%  |

## What was wrong with the reasoning

The note argued that vLLM's PagedAttention admits more concurrent sessions and
that TensorRT-LLM gives that up for throughput. TensorRT-LLM v0.9.0 already had
a paged KV cache and in-flight batching, so the premise was false, and the
session-count question was never measured.
