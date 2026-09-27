---
title: "cluster-ops-skills"
date: 2026-08-23
lastmod: 2026-09-27
description: "Eleven operator runbooks for self-managed Slurm and GPU clusters, packaged as Agent Skills, each naming the wrong conclusion it exists to prevent and the evidence it rests on."
summary: "Eleven operator runbooks for Slurm and GPU clusters, packaged as Agent Skills, each naming the wrong conclusion it exists to prevent."
tags: [slurm, agent-skills, runbooks, sre]
status: "Validated offline · not scored on the benchmark"
stage: "built"
repo: "https://github.com/Zhanyl-tech/cluster-ops-skills"
weight: 10
ShowToc: false
---

**[github.com/Zhanyl-tech/cluster-ops-skills](https://github.com/Zhanyl-tech/cluster-ops-skills)** · Python · MIT

<p class="project-status"><span class="status status-built">built</span>
Eleven runbooks, a validator and a claims ledger; <code>cluster-ops-skills
validate</code> reported 11 skills with 0 problems on 2026-09-27. Runbooks
recommend; they execute nothing. <strong>Whether loading them improves an
agent's diagnosis has not been measured.</strong></p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26. Merge or push it before publishing. -->

**The expensive mistakes on a cluster are not missing information; they are
wrong confident diagnoses:** recommending a priority-weight change as the fix
for low utilisation, or reporting that a storage stall halted scheduling when
jobs were completing throughout. So every skill has three mandatory sections,
enforced by the validator: the steps, *What not to conclude* (the plausible
wrong answer and why it is wrong), and *Escalate when*.

## What each runbook rests on

The evidence under the eleven varies a lot, and the repository says which is
which:

- **Reproduced on the benchmark's emulated cluster:**
  `accounting-path-stalled` (slurm-rca-bench S01: one fully probed run, plus a
  second run that confirmed the queue-depth signal) and `state-save-unwritable`
  (S06, one run, a permission failure only; a hung mount is not measured).
- **Observed on a kind cluster:** `slinky-authkey-rotation`, from
  [slinky-gitops](/projects/slinky-gitops/), where the rotation was seen to
  fail on Slinky v1.2 — verify by key hash, not by exit code or new pods.
- **Documented behaviour, a designed scenario, or a tool's design:** the other
  eight, from the Slurm documentation, benchmark scenarios that are designed
  but unmeasured or blocked, and the simulator (whose figures are synthetic, and
  labelled so).

An earlier version of this page said nine of the eleven "encode a failure that
has been measured rather than imagined". Only the three above rest on an
observed failure, each on a single test cluster.

Every figure a runbook quotes has an entry in a claims ledger that says whether
it was measured, documented upstream, or is only an illustration, with a link
for the first two; the validator fails a skill whose figure has no entry. The
validator also checks that every tool, topic and filter a runbook tells the
agent to use exists on the [slurm-mcp](/projects/slurm-mcp/) surface it is
written against.

The odd one out is `evidence-is-gone`, about deciding an incident is *not*
diagnosable and abstaining. It exists because the benchmark awards full credit
for abstention on its deliberately undiagnosable scenarios. Treating "stop and
hand off" as part of a runbook is not new; this is the Slurm-specific version.

**Slurm-shaped.** The Kubernetes side of a hybrid fleet is not covered beyond
the Slinky rotation runbook.
