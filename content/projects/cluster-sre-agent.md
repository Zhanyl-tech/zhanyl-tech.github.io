---
title: "cluster-sre-agent"
date: 2026-08-01
lastmod: 2026-09-27
description: "An LLM agent for Slurm incident diagnosis, built as five ablatable configurations. The dependency graph and the read-only tool guard are built; the agent configurations are not, and no accuracy has been measured."
summary: "An LLM agent for Slurm incident diagnosis, built as five ablatable configurations. The graph and the read-only guard are built; no accuracy has been measured."
tags: [slurm, llm-agents, dependency-graph, read-only, python]
status: "Graph and guard built · agent configurations A–E not built"
stage: "partial"
repo: "https://github.com/Zhanyl-tech/cluster-sre-agent"
weight: 8
ShowToc: true
---

**[github.com/Zhanyl-tech/cluster-sre-agent](https://github.com/Zhanyl-tech/cluster-sre-agent)** · Python · MIT

<p class="project-status"><span class="status status-partial">partial</span>
Built and tested: the failure-propagation graph and the read-only command
guard. <strong>Not built: the agent loop (configurations A–E) and any MCP
server</strong>, so no diagnosis accuracy has been measured and the results
table is empty.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26. Merge or push it before publishing. -->

Scored against [slurm-rca-bench](/projects/slurm-rca-bench/), and built as
five configurations that differ by one layer at a time, because the comparison
between them is the finding:

| | adds | question |
|---|---|---|
| **A** | raw LLM + shell (every command still passes the guard) | within-ablation baseline |
| **B** | + read-only tools, packaged as an MCP server would expose them | do packaged tools help? |
| **C** | + the explicit dependency graph | **the hypothesis** |
| **D** | + multi-agent specialists | does splitting evidence help? |
| **E** | + calibrated abstention | does knowing when to stop help? |

If C does not beat B, that is published as the result. A known threat to
validity is stated up front: the graph's measured edges come from the same runs
that set two scenarios' ground truth, so any C-versus-B comparison has to
report those scenarios separately.

## The graph refuses the folk model

Edges record whether a failure actually *propagates*, and how strongly, not
merely that a dependency exists. Each edge says whether it was measured,
documented or inferred:

```
$ csa stats          # run on 2026-09-27
  12 edges, 4 measured (33%)
  documented 3, inferred 5
```

An earlier version of this page said 62% measured: three edges were labelled
measured with no recorded run behind them. Three hardware edges were also
labelled documented with nothing cited. All six have been relabelled.

```
$ csa causes slurm.scheduler        (excerpt)

  documented slurm.config             1 hop(s)  slurm.config → slurm.scheduler
  documented slurm.slurmctld          1 hop(s)  slurm.slurmctld → slurm.scheduler
  inferred   storage.state_save       2 hop(s)  storage.state_save → slurm.slurmctld → slurm.scheduler
             only through an untested failure mode: a StateSaveLocation *stall* (writes block instead of failing), which S06's caveats name as a candidate for blocking slurmctld; S06 measured the error mode only

  ruled out at halts by measurement, within this graph:
    slurm.slurmdbd           slurm.slurmdbd → slurm.scheduler only degrades
    db.mysql                 slurm.slurmdbd → slurm.scheduler only degrades
    storage.shared_fs        slurm.slurmdbd → slurm.scheduler only degrades

  not covered by those measurements:
    slurm.slurmdbd → slurm.scheduler:
      - accounting-queue saturation: the DBD agent queue peaked at 6, while slurm.conf documents a MaxDBDMsgs floor of 10000
      - AccountingStorageEnforce=associations or limits (S08 found the benchmark cluster set to none)
      - stalls longer than the roughly fifteen minutes observed
```

Being able to say *"I checked the accounting path and, in the regime that was
measured, it cannot produce this symptom"* is worth as much as naming the
cause, and the last section says exactly where each measurement stops. A
measurement covers only the failure mode it exercised: the benchmark measured a
`StateSaveLocation` that *errors*, which only degrades the controller, so
`storage.state_save` stays on the list as an inferred cause through the
untested *stall* mode rather than being ruled out. (An earlier version of the
graph, and of this page, listed it as ruled out by measurement.)

**Severity composes along a path and does not compose transitively.** The first
version of the traversal got this wrong and a test caught it: every arrow in
`mysql → slurmdbd → slurmctld → scheduler` exists, so a naive walk concludes the
database can stop scheduling, reintroducing the model the benchmark refuted. A
path is only as strong as its weakest link.

## Read-only is a control, not a request

A prompt saying "only use read-only commands" fails open. The guard every
execution path calls is an **allowlist**: eight read tools, named bare and run
by absolute path from trusted directories; every option spelled exactly as the
tool's own parser spells it (so `--res` is not taken for `--reset`); full-word
read subcommands only. The first version was a denylist, and an audit got
`scontrol -o shutdown`, `scontrol upd PartitionName=debug State=DOWN` (scontrol
expands `upd` to `update`), `sacctmgr -i delete user x`, `sdiag -r` and a bare
`scontrol` (which reads commands from stdin) through it. The tests now cover every
`scontrol` and `sacctmgr` command on the man pages and every abbreviation of
every write, and CI fails if any listed write is allowed.

## Model

Every configuration is to run the same model, pinned as `claude-opus-5` for
reproducibility, so the ablation isolates architecture rather than model
choice. Configuration A is a baseline within this ablation, not comparable to
published numbers from other harnesses.
