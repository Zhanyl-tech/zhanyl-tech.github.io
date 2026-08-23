---
title: "cluster-ops-skills"
date: 2026-08-23
description: "Production HPC and GPU cluster runbooks packaged as loadable Agent Skills, each one naming the wrong diagnosis it exists to prevent."
summary: "Production HPC and GPU cluster runbooks packaged as loadable Agent Skills, each one naming the wrong diagnosis it exists to prevent."
tags: [slurm, hpc, agent-skills, runbooks, sre]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/cluster-ops-skills"
weight: 8
ShowToc: false
---

**[github.com/Zhanyl-tech/cluster-ops-skills](https://github.com/Zhanyl-tech/cluster-ops-skills)** · Python · MIT

Eleven runbooks for on-premises Slurm operations, written as loadable Agent
Skills.

**The expensive mistakes on a cluster are not missing information — they are
wrong confident diagnoses.** Recommending a priority-weight change that
measurement shows does nothing. Reporting that a storage stall halted
scheduling when jobs were completing throughout. So every skill carries a
mandatory *What not to conclude* section naming the plausible wrong answer, and
an *Escalate when* section, both enforced by a validator that fails the build.

Nine of the eleven map onto a fault family that
[slurm-rca-bench](/projects/slurm-rca-bench/) already reproduces — storage,
accounting, controller, GPU, fabric, scheduler config — so each encodes a
failure that has been measured rather than imagined. The validator also fails
any skill quoting a percentage without a link to the repo that measured it.

The odd one out is `evidence-is-gone`, about deciding an incident is *not*
diagnosable and abstaining. It exists because the benchmark awards full credit
for abstention on its deliberately undiagnosable scenarios and zero for naming
even the most plausible cause. A confident wrong diagnosis sends someone to
replace healthy hardware and stops the search.

Whether loading these improves an agent's accuracy is unmeasured, and the
harness for answering that is the benchmark above.
