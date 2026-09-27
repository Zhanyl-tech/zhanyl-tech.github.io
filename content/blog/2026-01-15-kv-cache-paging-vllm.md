---
title: "How KV-Cache Paging Works in vLLM — and Why It Matters for Production"
date: 2026-03-28
lastmod: 2026-09-26
description: "A walkthrough of PagedAttention, the KV-cache memory manager from the vLLM paper (Kwon et al., SOSP 2023), and why paging matters for serving many concurrent LLM sessions."
tags: [vllm, inference, kv-cache, gpu, memory, production, llm]
summary: "A walkthrough of PagedAttention, the KV-cache memory manager from the vLLM paper, and why paging matters for serving many concurrent LLM sessions."
ShowToc: true
draft: false
---

*Updated 26 September 2026: the figures below are now attributed to the vLLM
paper they come from, two overstatements are corrected, and a stale statement
about FlashAttention is fixed. The date above is when this post was first
committed to the site; it previously carried an earlier date. See
[corrections](/corrections/).*

Most articles about vLLM lead with the benchmark numbers. I want to start with the problem it actually solves, because understanding *why* KV-cache paging exists is what makes the implementation decisions make sense.

## The Problem: Memory Fragmentation Kills Concurrency

When you serve an LLM in production, you're not running one request at a time. You have dozens to hundreds of concurrent sessions, each at a different point in its generation. Each session needs to store its KV-cache — the key-value tensors computed from every token processed so far.

The naive approach allocates a contiguous block of GPU memory for each session's KV-cache at the start of the request. This causes two problems.

**Problem 1: You have to pre-allocate for the worst case.** If your model supports 8K context and you pre-allocate for the maximum, most sessions use a fraction of that. A 100-token conversation is holding memory reserved for 8K tokens. The vLLM paper measured this in the serving systems it compared against: "only 20.4% - 38.2% of the KV cache memory is used to store the actual token states in the existing systems" ([Kwon et al., arXiv:2309.06180](https://arxiv.org/abs/2309.06180)).

**Problem 2: Fragmentation blocks new sessions.** After serving a few hundred requests, your GPU memory looks like Swiss cheese — many small free blocks that collectively add up to enough space for a new KV-cache, but no single contiguous block large enough to fit it. New requests queue up even though memory is technically available.

This is exactly the same problem that motivated virtual memory and paging in operating systems. vLLM's PagedAttention applies the same solution.

## PagedAttention: Paging for KV-Caches

PagedAttention divides GPU memory into fixed-size *physical blocks*. Each block holds KV tensors for a fixed number of tokens; the paper sets vLLM's default block size to 16, "large enough to efficiently utilize the GPU and small enough to avoid significant internal fragmentation in most workloads". A session's KV-cache is stored in a linked sequence of physical blocks, which don't need to be contiguous.

A *block table* maps each session's logical KV positions to physical block addresses. The attention computation is modified to follow this indirection — instead of reading from a contiguous buffer, it reads from wherever the block table points.

```
Session A KV-cache:
  Logical block 0 → Physical block 47
  Logical block 1 → Physical block 12
  Logical block 2 → Physical block 91

Session B KV-cache:
  Logical block 0 → Physical block 3
  Logical block 1 → Physical block 58
```

The blocks themselves are small and fixed-size, so they can be allocated from a pool. When a session completes, its blocks are returned to the pool and become immediately available to new sessions. That removes external fragmentation. Internal fragmentation remains, bounded to the last, partly filled block of each sequence: in the paper's words, "vLLM limits all the memory wastes for a request within one block". The abstract's phrase is "near-zero waste", not zero.

## What This Changes in Practice

The practical effect is significant, and the numbers belong to the paper, not to me: it reports 20.4–38.2% of KV-cache memory holding token state in the systems it compared against, and vLLM throughput "2-4× with the same level of latency compared to the state-of-the-art systems, such as FasterTransformer and Orca" ([abstract](https://arxiv.org/abs/2309.06180)). That is a throughput figure. More concurrent sessions is the mechanism behind it (more requests fit in the same memory, so the batch is larger), but the paper's headline is not a session count, and I have not measured one.

There's another benefit that matters for agentic workloads specifically: **prefix caching becomes practical**. When multiple sessions share the same system prompt (common in multi-agent deployments), those prefix blocks can be shared across sessions — physically shared, not copied. Sessions that differ only in the user-turn portion of their context can share all the prefix KV-cache blocks.

## The Attention Kernel Change

The attention computation itself needs modification to work with paged KV-caches. The PagedAttention kernel takes the block table as an additional input and gathers blocks during the attention computation. (An earlier version of this post said "standard FlashAttention reads from a single contiguous KV tensor". That has been out of date since FlashAttention 2.5, whose changelog reads "2.5: Paged KV cache", with a `block_table` argument to `flash_attn_with_kvcache` — [FlashAttention README](https://github.com/Dao-AILab/flash-attention).)

This is where the CUDA work lives. The kernel processes each query position by looking up which physical block contains its corresponding key-value data, loading that block, and performing the attention dot products. The scatter/gather pattern adds some overhead compared to reading from contiguous memory, but it's small relative to the memory savings.

## When This Matters Most

Not every deployment benefits equally from PagedAttention. Short sessions with simple prompts on high-throughput pipelines may see minimal benefit. The gains are largest when:

- Sessions have widely varying lengths (long-tail distribution)
- Many sessions share the same system prompt or prefix
- You're running close to GPU memory capacity with concurrent requests
- Generation length is unpredictable at request time

That last point is particularly relevant for agentic use cases, where reasoning chains can expand significantly as the agent encounters unexpected tool results. Pre-allocating for a worst-case chain length isn't practical when you don't know what the chain looks like.

## What I'd Look for Next

The benchmark implications of all this are non-obvious. Throughput numbers that measure tokens-per-second on a single batch don't capture the memory utilization improvements. The right benchmark for a production serving system is: *how many concurrent sessions at what latency percentile, at what memory utilization?*

I have not run that benchmark. *(An earlier version of this post said "that's the test I'm running next" and linked a throughput comparison that has since been withdrawn; see [corrections](/corrections/).)*

---

**Source:** Woosuk Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention*, SOSP 2023, [arXiv:2309.06180](https://arxiv.org/abs/2309.06180).

*Related: [LServe and SampleAttention: what sparse attention changes in prefill and decode](/blog/2026-01-30-lserve-sampleattention-sparse-attention/)*
