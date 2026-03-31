---
title: "LServe and SampleAttention: What Sparse Attention Actually Changes in Prefill and Decode"
date: 2026-01-30
description: "A technical walkthrough of two recent sparse-attention papers. LServe turns structured sparsity into an end-to-end serving system for both prefilling and decoding, while SampleAttention explains which sparse patterns matter and why CRA is a strong runtime proxy for accuracy."
tags: [sparse-attention, llm-serving, prefill, decoding, kv-cache, lserve, sampleattention, gpu-inference]
summary: "A technical walkthrough of how LServe and SampleAttention use structured sparsity, what changes in prefilling vs decoding, and why CRA is a useful accuracy proxy."
ShowToc: true
draft: false
---

Sparse attention is easy to talk about in the abstract and much harder to reason about in production. The useful question is not "is attention sparse?" but *which structure can you exploit cheaply enough that the runtime win survives contact with a GPU kernel*.

Two recent papers answer that question from different angles:

- **LServe** asks how to turn structured sparsity into a full serving system for long-context LLMs, including both **prefill** and **decode**.
- **SampleAttention** asks what sparse patterns dominate real attention maps during **prefill**, and how to choose them adaptively without paying the cost of dense attention first.

**Visual summary:** [review the 4-slide deck](/slides/lserve-sampleattention.html) or [download the PDF version](/slides/lserve-sampleattention.pdf)

![LServe and SampleAttention sparse attention overview](/images/vizpub/lserve-sampleattention-overview.svg)

My read is that these papers are complementary.

SampleAttention gives the clean conceptual picture: attention sparsity is not random noise, and two recurring structures explain a surprising amount of the retained attention mass. LServe then takes the next systems step: if sparse structure is real, how do you make it hardware-friendly enough to speed up actual serving, especially once decoding and KV-cache pressure dominate?

## TL;DR

- **LServe:** use different sparse mechanisms for different serving bottlenecks. Prefill skips KV blocks; decode prunes KV pages.
- **SampleAttention:** two sparse patterns explain much of the useful structure in prefill attention. Columns preserve global anchors; slashes preserve local continuity.
- **CRA:** a practical runtime proxy for accuracy because it tracks how much important attention mass remains after sparsification.

## The Shared Idea: Sparsity Has Structure

Both papers reject the naive version of sparse attention where you try to keep an arbitrary subset of individual scores. That kind of fine-grained sparsity usually looks good on paper and bad in kernels.

Instead, both look for **structured** sparsity:

- structures that align with how GPUs process attention in blocks or pages
- structures that can be selected cheaply at runtime
- structures that preserve enough attention mass to keep model quality near dense attention

That last point matters. If sparsity selection is too expensive, you just moved work around. If the pattern is too rigid, quality collapses on difficult prompts. The interesting part of both papers is the compromise between **accuracy**, **adaptivity**, and **kernel efficiency**.

## How LServe Works in the Prefill Phase

The key observation in LServe is that attention kernels are still sequential along the KV dimension, even when other dimensions are parallelized. That means a practical speedup comes from **reducing the number of KV blocks the kernel iterates over**, not from trying to skip a few scalar operations inside each block.

In prefill, LServe uses a **unified block-sparse attention** formulation:

- the KV history is partitioned into blocks
- the most recent block is always computed
- older blocks are either fully kept or fully skipped

This is an important design choice. Block-level skipping maps much better to GPU execution than token-level irregular masks. It reduces the number of sequential attention iterations in a way the kernel can actually exploit.

On top of that, LServe adds **static sparsity** inspired by streaming-style attention. The paper converts roughly half of the heads into **streaming heads** using a Lambda-shaped mask. Intuitively, those heads keep the recent local context plus a compressed path for longer-range information, making them much cheaper than full dense heads.

So in the prefill phase, LServe is doing two things at once:

1. It changes the *unit of sparsity* from individual tokens to **blocks**.
2. It changes part of the model's attention pattern from dense heads to **cheap streaming heads**.

The systems payoff is that both sparse and dense-style heads can still be executed through unified kernels rather than as completely separate code paths.

## How LServe Works in the Decoding Phase

Decode is a different problem. Prefill is dominated by quadratic attention over a large prompt. Decode is only one query token at a time, but it is still expensive because the query may need to read a very large KV cache, and that process becomes increasingly **memory-bound**.

This is where LServe's second idea shows up: **page-level dynamic sparsity**.

The paper's claim is that for long-context capability you often do **not** need to read the entire KV cache at decode time. Instead, for a given query, only a relatively small number of KV pages are genuinely important. More specifically, LServe argues that the required number of useful KV pages can remain roughly constant even as total context length grows.

That leads to a different sparse mechanism for decode:

- KV cache is already organized as pages
- a **hierarchical page selector** scores which pages matter for the current query
- only the selected pages are loaded into the decode attention path
- selection results are reused across nearby tokens to amortize overhead

This is the crucial distinction between LServe's two phases:

- **Prefill** uses **block sparse attention over many query tokens**
- **Decode** uses **page selection over a huge KV cache for one query token at a time**

LServe also combines this with **KV-cache quantization**. That makes sense because quantization and sparsity attack different parts of the decode bottleneck:

- sparsity reduces how many pages you touch
- quantization reduces the cost of touching each selected page

That is why the paper frames the gains as multiplicative rather than redundant.

## A Short Answer to the First Question

If I compress the paper into one sentence:

**LServe uses hardware-friendly structured sparsity in both phases, but it uses different structures for different bottlenecks: block-sparse + streaming-head acceleration in prefill, and query-aware page pruning + quantized KV access in decode.**

That is the most important mental model to keep.

## What SampleAttention Says the Sparse Pattern Actually Looks Like

SampleAttention is focused on the **prefill** problem, especially long-context TTFT. The paper argues that earlier sparse methods miss accuracy because they assume a fixed sparsity budget or a fixed pattern family per head.

Its empirical point is stronger: attention patterns vary across

- heads
- prompts
- models

but they still tend to contain two dominant structures.

## The Two Sparse Patterns That Matter

According to SampleAttention, the two sparse patterns that substantially contribute to the attention score are:

### 1. Column Pattern

The **column pattern** corresponds to a small set of key positions that attract attention from many query positions.

Semantically, this represents **global contextual anchors**. The paper explicitly connects this to the idea of an **attention sink**: a few key tokens behave like globally important reference points, so many rows of the attention matrix want to keep them.

If you think operationally, columns are where the model is saying:

"Many different query tokens still need access to these same global tokens."

That is why column stripes are a good sparse primitive for preserving long-range global information.

### 2. Slash Pattern

The **slash pattern** represents diagonal or near-diagonal structure, where query tokens attend to key tokens at regular relative offsets.

Semantically, this captures **local or position-relative continuity**, especially recent-context behavior. The paper uses the local window as the canonical example. In plain English: a token often needs the nearby tokens around it, and that local dependency shows up as slash-like structure in the attention map.

If columns preserve *global anchors*, slashes preserve *local continuity*.

That pairing is why the paper is compelling: together, columns and slashes are expressive enough to approximate many real attention maps without needing an unwieldy catalog of special cases.

## How CRA Is Defined

SampleAttention introduces **CRA**, or **Cumulative Residual Attention**, as its accuracy-oriented control signal.

The paper defines CRA as the **minimum sum of remaining attention probabilities per query after sparsification**.

The intuition is simple:

- start from dense attention probabilities
- apply a sparse mask
- for each query, ask how much probability mass remains in the kept entries
- take the minimum across queries

So CRA is a worst-case retention measure. It is not asking whether the *average* query kept enough attention mass. It is asking whether the **most damaged query** still retained enough of the original attention probability.

That makes it a much better safety metric than a fixed global sparsity ratio.

## Why CRA Is an Indicator of Accuracy

The reason CRA tracks accuracy is that it approximates **attention recall**.

If sparsification removes too much probability mass for some query, then the output for that query is being computed from an incomplete set of keys and values. Once that loss gets large enough, you should expect downstream representation quality and task accuracy to degrade.

CRA works as an indicator because it captures exactly that failure mode:

- a higher CRA means the sparse pattern retained more of the important attention mass
- a lower CRA means at least one query likely lost too much information

The paper reports a consistent positive correlation between CRA thresholds and model accuracy across tasks and models. That does not make CRA a proof of correctness, but it does make it a practical control knob for the efficiency versus accuracy trade-off.

In other words, CRA gives SampleAttention a way to say:

"Keep the sparse pattern just large enough that the worst query still retains enough useful attention."

That is a far better runtime policy than "always keep 10% of tokens" or "always use this head's offline pattern."

## How SampleAttention Approximates CRA Efficiently

Computing exact CRA would require computing dense attention first, which defeats the point. SampleAttention gets around this with a **two-stage runtime approximation**.

### Stage 1: Query-Guided Chunked Sampling

Instead of evaluating the full attention matrix, the method samples attention scores from a few query blocks spread across the sequence. The goal is to avoid the bias of only looking at the last queries, since some heads show strong structure in one region of the matrix and different structure elsewhere.

From those sampled query blocks, SampleAttention accumulates approximate scores along two directions:

- **columns**
- **slashes**

This produces a cheap summary of which global columns and which local slash bands are likely to matter.

### Stage 2: Score-Based Key-Value Filtering

Once those approximate scores are available, SampleAttention picks the minimal amount of sparse structure needed to satisfy the desired threshold.

The paper splits the target into two thresholds:

- `alpha_c` for columns
- `alpha_s` for slashes

Then it:

- reduces the sampled scores at block granularity
- determines how many column and slash blocks are needed
- runs top-k selection independently in each direction
- extends those selected indices into full column/slash patterns
- merges them into the final sparse mask

This decomposition is important because it avoids an expensive joint search over all column-slash combinations. You get an adaptive sparse mask without paying combinatorial cost.

## My Take: These Papers Fit Together

The clean way to connect the two papers is this:

- **SampleAttention** explains *what sparse structure looks important during prefilling* and provides a runtime metric, CRA, for preserving quality.
- **LServe** explains *how to turn structured sparsity into a complete serving stack*, especially once decoding, page selection, and KV-cache bandwidth matter.

SampleAttention is more about the **selection principle**.
LServe is more about the **serving-system realization**.

That also explains why LServe spends so much energy on decode. A lot of sparse-attention discussion stops at TTFT. Real serving systems cannot stop there, because long outputs and reasoning-heavy workloads shift the bottleneck toward decode-time KV access.

## Why This Matters in Production

If you are building long-context inference infrastructure, the important lesson is not just that attention is sparse. It is that **serving-time bottlenecks move**, and the sparse structure you can exploit depends on where the bottleneck lives.

- In prefill, the enemy is the cost of walking a long KV history over many query tokens.
- In decode, the enemy is the bandwidth cost of repeatedly touching a large KV cache for one query token at a time.

That is why these papers are more useful together than separately. One clarifies the sparse structure. The other clarifies the serving architecture.

## The Practical Mental Model

If I had to keep only three takeaways from these papers, they would be:

1. **Prefill and decode are different optimization problems.** You should not assume one sparse mechanism is optimal for both.
2. **The winning sparse patterns are structured, not arbitrary.** Columns preserve global anchors; slashes preserve local continuity.
3. **Accuracy needs a runtime proxy.** CRA is useful because it measures how much important attention mass survives sparsification rather than relying on a fixed sparsity budget.

That combination is what makes these papers worth reading for anyone working on long-context serving rather than only model-side architecture.

## References

- **LServe: Efficient Long-sequence LLM Serving with Unified Sparse Attention**: [arXiv:2502.14866](https://arxiv.org/abs/2502.14866)
- **SampleAttention: Near-Lossless Acceleration of Long Context LLM Inference with Adaptive Structured Sparse Attention**: [arXiv:2406.15486](https://arxiv.org/abs/2406.15486)

---

*Related: [How KV-Cache Paging Works in vLLM — and Why It Matters for Production](/blog/2026-01-15-kv-cache-paging-vllm/)*
