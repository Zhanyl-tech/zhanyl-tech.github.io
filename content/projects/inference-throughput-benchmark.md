---
draft: true  # Withdrawn 2026-09-26: the numbers below are not physically plausible and have no artefact. See the comment at the top of the body and /corrections/.
title: "vLLM vs TensorRT-LLM: Inference Throughput"
date: 2026-01-20
description: "WITHDRAWN. A throughput comparison of vLLM and TensorRT-LLM on Llama-3 70B whose numbers could not be backed by any artefact and are not physically plausible on the stated hardware."
summary: "WITHDRAWN. A throughput comparison whose numbers are not physically plausible on the stated hardware."
tags: [vllm, tensorrt-llm, inference, benchmark]
status: "Withdrawn"
stage: "planned"
weight: 6
ShowToc: false
---

<!--
WITHDRAWN on 2026-09-26. draft: true keeps this page off the public site; it
is kept in the repository, not deleted, so the record of what was published
stays inspectable. The public note is on /corrections/.

Why it was withdrawn (every figure below was checked on 2026-09-26):

1. The setup cannot run as stated. Llama-3-70B has 70,553,706,496 parameters
   (Hugging Face model card / API). In BF16 that is about 141 GB of weights,
   and the stated hardware is ONE A100 80GB with "no quantization". The model
   does not fit.
2. The batch-1 numbers exceed the memory-bandwidth ceiling. Batch-1 decode
   reads every weight once per generated token. 141.1 GB / 2,039 GB/s (NVIDIA
   A100 80GB SXM datasheet bandwidth) = 69 ms per token, i.e. at most about
   14 tokens/s. The table claims 412 and 487 tok/s at batch 1, roughly 30x
   that ceiling.
3. The conclusion rests on a false premise. TensorRT-LLM v0.9.0, the version
   named here, lists "Paged KV Cache for the Attention" and "In-flight
   Batching" in its README, so "TensorRT-LLM trades paging away for
   throughput" is wrong, and the page itself says KV-cache pressure was not
   measured.
4. There is no artefact: no repository, scripts, logs, or hardware inventory.
   The page is dated 2026-01-20; git first records its content on 2026-03-28
   (commit ac8c811, "seed content").

What evidence would be needed to republish anything under this title:

- a public repository with the exact launch scripts, pinned engine versions
  (vLLM, TensorRT-LLM, CUDA, driver) and the build/quantization flags;
- a configuration that fits the hardware: for example tensor parallelism
  across 2x A100-80GB for a 70B model in BF16, or an 8B model on one GPU,
  stated with the GPU model and count and nvidia-smi output;
- raw per-request logs (arrival time, input/output tokens, TTFT, per-token
  latency) from which every table cell can be recomputed by a committed
  script, with repeat runs and their spread;
- a workload that measures the claim actually of interest: concurrent
  sessions and p50/p99 latency at a fixed KV-cache budget under a realistic
  arrival process, not static-batch throughput;
- a sanity check against the bandwidth ceiling above, printed with the
  results.

Until then nothing on this page may be quoted anywhere on the site.
-->

*Withdrawn. See [corrections](/corrections/).*

**Setup as originally stated.** Single NVIDIA A100 80GB SXM · Llama-3 70B (BF16) · vLLM 0.4.1 ·
TensorRT-LLM 0.9.0 · 512 input → 128 output tokens · no quantization, no
speculative decoding. (This configuration does not fit in 80 GB; see the
comment at the top of this file.)

| batch | vLLM (tok/s) | TensorRT-LLM (tok/s) | delta |
|---|---|---|---|
| 1 | 412 | 487 | +18% |
| 4 | 1,380 | 1,710 | +24% |
| 8 | 2,240 | 2,890 | +29% |
| 16 | 3,180 | 4,210 | +32% |

*The table above is withdrawn and kept only as the record of what was
published. It has no artefact behind it.*

## What the original page argued, and what was wrong with it

The original argument was that vLLM's PagedAttention admits more concurrent
sessions before running out of memory, and that TensorRT-LLM "trades that
flexibility for raw throughput". The second half is false for the version
named: the TensorRT-LLM v0.9.0 README lists a paged KV cache and in-flight
batching. Which engine admits more sessions at a given KV-cache budget is an
empirical question this page never measured.

## What this does not measure

- **Continuous batching.** Real agentic traffic does not arrive in uniform
  batches.
- **KV-cache pressure.** The session count at which each engine degrades.
- **Latency percentiles.** Throughput hides p99 variance.
- **Quantization.** INT8 and FP8 would change the picture.
