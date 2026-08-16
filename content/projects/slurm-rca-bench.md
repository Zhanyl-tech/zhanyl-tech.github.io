---
title: "slurm-rca-bench"
date: 2026-08-01
description: "The first public incident-diagnosis benchmark for HPC schedulers — ten reproducible failure scenarios with measured ground truth and degenerate baselines."
summary: "The first public incident-diagnosis benchmark for HPC schedulers — ten reproducible failure scenarios with measured ground truth and degenerate baselines."
tags: [slurm, hpc, benchmark, root-cause-analysis, llm-agents]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/slurm-rca-bench"
weight: 1
ShowToc: false
---

**[github.com/Zhanyl-tech/slurm-rca-bench](https://github.com/Zhanyl-tech/slurm-rca-bench)** · Python · MIT

Every existing root-cause-analysis benchmark for LLM agents is cloud
microservices. This one is an HPC scheduler.

## The thesis

Published RCA scores are poor, but improving fast with model generation — and
quoting a stale number would misrepresent both facts. On OpenRCA's unchanged
335-failure task set: 11.34% (Claude 3.5, ICLR'25) → 27% (Opus 4.5) → **35%**
(Opus 4.6). On ORCA-bench, 48.8% RCA depth with partial credit.

Even so, the best current numbers leave roughly two thirds of incidents
misdiagnosed. The structural reason is the graph: cloud topologies are huge,
dynamic and undocumented, so an agent must infer the shape of the system and
diagnose the fault simultaneously. A Slurm control plane is the opposite — a
dozen components, static between deploys, identical at every site.

## The first finding was about the benchmark itself

The flagship scenario was built around the model everyone repeats: a storage
stall backs up through the accounting path until the controller's queues fill
and scheduling halts, about thirteen minutes later.

Then I measured it. With the database suspended for fifteen minutes, jobs
submitted, started and completed normally throughout. `sinfo` never stalled.
**Slurm degrades the accounting path independently of scheduling.**

A second storage failure mode — `StateSaveLocation` unwritable — fails loudly
and instantly instead, rejecting every submission with an I/O error while
running jobs continue untouched. Two of three storage paths measured, and
neither produces the silent delayed halt the folk model predicts.

The scenario now ships documenting its own refutation.

## Baselines are the number to ask for first

A benchmark reporting only "the agent scored 0.52" tells you nothing, because
you cannot know that answering the same node to every task scores 0.50. The
suite computes that floor from ground truth alone — and it audited itself: at
five scenarios, `always-db.mysql` scored **0.290** without reading any
telemetry. Adding scenarios whose causes lie elsewhere cut it to **0.145**, and
a test now fails the build if it climbs back.

## Two scenarios have no answer

They exist to penalise confident guessing. Abstention scores full marks;
naming any plausible cause scores zero, including the one a human would pick.
Without them a benchmark rewards fluent overconfidence — precisely the failure
mode that makes an agent dangerous on an on-call rotation.
