---
title: "Projects"
description: "Open-source GPU-cluster tooling and the benchmarks that check it. Each entry says whether it is built, partial or planned, and what it was tested against."
---

Every project links to its repository. <span class="status status-built">built</span>
means code and tests exist; <span class="status status-partial">partial</span>
means some named parts do not; <span class="status status-planned">planned</span>
means not built. **None of it has run on a production GPU cluster.** Where
something was measured, the entry says on what, and numbers that turned out to
be wrong are listed on [corrections](/corrections/).

## Scheduler evaluation across Slurm and Kubernetes

**[k8s-gpu-scheduler-lab](/projects/k8s-gpu-scheduler-lab/)**
<span class="status status-partial">partial</span> — a controlled comparison of
Kubernetes GPU schedulers on the same traces, on a real control plane with
simulated GPU nodes (kind + kwok). K0, the default scheduler, and four
degenerate baselines are built, and a Phase 2 measurement harness (repeats,
spreads, queue parity) is built but has not run on a cluster. Kueue, Volcano,
NVIDIA's Volcano bin-packing and KAI are not built. Its most useful finding so
far is about a metric: the same largest-first run read 0.0% fragmentation under
a queue-relative definition and 55.6% under a fixed reference (Phase 1, one
run), so a fragmentation claim that does not state its definition cannot be
reproduced. I have not found a published controlled comparison on an identical
trace and substrate; [Radiant's 2026 comparison](https://radiant.co/blog/benchmarking-kueue-volcano-and-slinky-on-radiant)
of Kueue, Volcano and Slinky used different GPUs for Kueue than for the others.

**[slurm-scheduler-lab](/projects/slurm-scheduler-lab/)**
<span class="status status-built">built</span> — a discrete-event model of
Slurm's multifactor priority, Fair Tree fairshare, backfill (Slurm-style
conservative by default, EASY as an option) and preemption. Reads a real
`slurm.conf`, replays `sacct` traces, and serves as the Slurm side (S0) of the
Kubernetes comparison. On its synthetic workload, backfill cut mean wait by a
median 3.8× over 20 seeds, and an extreme job-size weight moved it by a
comparable amount; a model, not a controller.

## Slurm on Kubernetes

**[slinky-gitops](/projects/slinky-gitops/)**
<span class="status status-partial">partial</span> — Slurm 26.05 on kind with
SchedMD's Slinky operator v1.2, in one command, plus an auth-key rotation that
measures its own result: it hashes the key inside every slurmd pod. On v1.2 the
new key does not reach slurmd, so the script rolls back and says so. Along the
way: `kubectl rollout restart` silently skips pods owned by Slinky's `NodeSet`
resource. No GitOps controller is wired up yet.

## GPU fleet health

Three Go tools built on one rule, never act on absent evidence. All three are
tested against simulators and synthetic trees, not hardware.

**[epilog-gpu-validator](/projects/epilog-gpu-validator/)**
<span class="status status-built">built</span> — a Slurm Epilog check that
drains a node for evidence of a persistent GPU fault. Slurm drains a node when
the Epilog exits non-zero, so a failed query without a documented
hardware-fault exit code, an unreadable field or an idle PCIe link exits 0;
report-only by default.

**[gpu-reaper](/projects/gpu-reaper/)**
<span class="status status-built">built</span> — finds allocated-but-idle GPUs
on Slurm and, only if enabled, drains and cancels. Observe by default; a gap,
stale sample or unreadable field is never read as idleness; a new dcgm-exporter
source is unverified and can only alert.

**[ib-slurm-exporter](/projects/ib-slurm-exporter/)**
<span class="status status-built">built</span> — attributes InfiniBand/RoCE
counters to the Slurm job using the HCA, refuses to attribute a port it can
see is shared (in its default mode kernel RDMA users are invisible to it), and
handles Slurm 26.05's SLUID-named cgroups (from the documentation; not
validated on a live 26.05 node).

## Measurement and agents

**[slurm-rca-bench](/projects/slurm-rca-bench/)**
<span class="status status-partial">partial</span> — an incident-diagnosis
benchmark for the Slurm control plane: ten scenarios, six runnable, scored
with partial credit against degenerate baselines. Its first finding was about
itself: the flagship chain, a stalled accounting database halting scheduling,
did not happen when measured on a Docker test cluster. The runnable suite is
currently degenerate (answering `db.mysql` to everything scores 0.333, above
its own 0.25 threshold), and it says so. No agent has been scored.

**[cluster-sre-agent](/projects/cluster-sre-agent/)**
<span class="status status-partial">partial</span> — an LLM diagnosis agent
built as five ablatable configurations. The failure-propagation graph (12
edges, 4 measured) and the read-only guard are built; the configurations are
not, so no accuracy has been measured.

**[slurm-mcp](/projects/slurm-mcp/)**
<span class="status status-built">built</span> — a read-only MCP server for
Slurm state. The allowlist of command shapes is enforced in code and tested
with 70 adversarial command lines; three tools with progressive disclosure.
Fixture-tested, not yet run against a real cluster.

**[cluster-ops-skills](/projects/cluster-ops-skills/)**
<span class="status status-built">built</span> — eleven operator runbooks as
Agent Skills, each naming the wrong conclusion it exists to prevent. A
validator enforces the sections and a claims ledger for every figure. Three of
the eleven rest on an observed failure, each on a single test cluster (two on
the benchmark's Docker cluster, one on kind); the rest on documentation or
design.

## Quantitative research infrastructure

**[research-platform](/projects/research-platform/)**
<span class="status status-partial">partial</span> — a point-in-time data layer
for backtesting: an append-only bitemporal store where every query takes an
as-of date. Phase 1 of 6; feature lineage and leakage detection are planned.
