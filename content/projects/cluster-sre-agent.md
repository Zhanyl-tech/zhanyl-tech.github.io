---
title: "cluster-sre-agent"
date: 2026-08-01
description: "Multi-agent diagnosis over an explicit cluster dependency graph — five ablatable configurations, specified before results existed."
summary: "Multi-agent diagnosis over an explicit cluster dependency graph — five ablatable configurations, specified before results existed."
tags: [slurm, llm-agents, mcp, multi-agent, observability]
status: "In Build"
repo: "https://github.com/Zhanyl-tech/cluster-sre-agent"
weight: 2
ShowToc: false
---

**[github.com/Zhanyl-tech/cluster-sre-agent](https://github.com/Zhanyl-tech/cluster-sre-agent)** · Python · MIT

Scored against [slurm-rca-bench](/projects/slurm-rca-bench/). Built as five
ablatable configurations, because the ablation *is* the finding:

| | |
|---|---|
| **A** | raw LLM + shell |
| **B** | A + read-only tools |
| **C** | B + the dependency graph — **the hypothesis** |
| **D** | C + multi-agent specialists |
| **E** | D + calibrated abstention |

## Status, stated plainly

The dependency graph and the read-only tool surface are **built and tested**.
The LLM configurations are **not** — so **no diagnosis accuracy has been
measured**, and the results table stays empty until it has been.

## The graph refuses the folk model

Edges record whether a failure actually *propagates*, not merely that a
dependency exists — and 62% of them are measured on a live cluster rather than
assumed:

```
$ csa causes slurm.scheduler

  measured   slurm.config      slurm.config → slurm.scheduler
  documented slurm.slurmctld   slurm.slurmctld → slurm.scheduler

  ruled out by measurement:
    slurm.slurmdbd   none — scheduling continues normally with accounting unavailable
```

Being able to say *"I checked the accounting path and it cannot produce this
symptom"* is worth as much as naming the cause.

**Severity composes along a path and does not compose transitively.** The first
version of the traversal got this wrong and a test caught it: every arrow in
`mysql → slurmdbd → slurmctld → scheduler` exists, so a naive walk concludes
the database can stop scheduling — reintroducing the exact model the benchmark
refuted. A path is only as strong as its weakest link.

## Read-only is a control, not a request

A prompt saying "only use read-only commands" fails open. The allowlist lives
in code, in the function every execution path calls, and the tests drive it
with what an agent actually reaches for at 3am — `scontrol update
NodeName=ALL State=DRAIN`, `scancel`, shell injection, absolute-path bypasses.
CI fails the build if any is permitted.
