---
title: "Corrections"
layout: "single"
url: "/corrections/"
summary: "What this site got wrong, what was withdrawn, and what was changed to match the repositories it describes."
description: "What this site got wrong, what was withdrawn, and what was changed to match the repositories it describes."
ShowToc: false
---

This site argues that a claim should say how it was measured. That has to
apply to the site too, so errors are listed here rather than silently edited.
Each entry says what was published, what was wrong, and what replaced it.

<!-- OWNER: the entries below were written on 2026-09-26 from an audit of the
site. If they go live later than that, keep the audit date and add the publish
date next to it. -->

## September 2026

**Withdrawn: "vLLM vs TensorRT-LLM" throughput numbers.** The project page
and the January 2026 lab note reported 412–4,210 tok/s for Llama-3 70B in BF16
on a single A100 80GB. That setup does not fit in 80 GB (about 141 GB of
weights), the batch-1 figures are roughly 30 times what the A100's memory
bandwidth allows for batch-1 decode, the conclusion rested on the false premise
that TensorRT-LLM 0.9.0 lacks a paged KV cache, and no scripts or logs exist.
Both pages are unpublished and kept in the repository as a record. Nothing
about inference throughput is claimed on this site until a run with published
scripts and raw logs exists.

**Corrected: the Slurm backfill result was a synthetic workload, one seed.**
The About page, the Projects page and the scheduler-lab page called the
backfill numbers (72.2% → 83.6% CPU utilisation, mean wait 1,913 → 374 min)
"measured" on "real job traces". They came from the simulator's synthetic
generator: 300 jobs, 16 nodes, seed 5, simulator version 0.1. Over 20 seeds of
that same code, the priority-weight sweep moved mean wait by a median 3.06×,
not the "about 40%" the write-up claimed, and on 3 of the 20 seeds it moved it
more than backfill did. The claim that time limits were "the real lever" was
never measured by that version. The [write-up](/experiments/2026-07-26-slurm-backfill-time-limits/)
now carries the correction at the top, with the commands.

**Corrected: the Slurm 25.11/26.05 upgrade note.** It said the renamed options
(`JobContainerType`, `ExclusiveUser`, `ExclusiveTopo`) would stop a config from
parsing after a restart. Slurm's own source shows the old names still parse:
`JobContainerType` logs a deprecation warning, and the two partition options
are still read. It also gave the wrong 26.05 release date and a wrong REST API
row. The [note](/experiments/2026-07-26-slurm-25-11-upgrade-notes/) is
corrected, with citations to the source, and points to the September security
releases.

**Corrected: the system map drew unbuilt parts as running.** Kueue, Volcano and
NVIDIA KAI appeared as the schedulers under comparison; none is built yet. The
map now puts built, partial or planned on every box. It also said the
InfiniBand exporter "refuses to attribute a shared device". It refuses only
when it can see that a port is shared, and in its default mode kernel RDMA
users (IPoIB, NFS/RDMA) are invisible to it; the map and the
[project page](/projects/ib-slurm-exporter/) now say so.

**Corrected: numbers that no longer matched their repositories.** The
dependency-graph share of measured edges, the slurm-mcp test and footprint
figures, the benchmark's degenerate floor, the epilog validator's scenario
table and research-platform's scope were all out of date or wrong; each project
page now quotes the current repository and says how the number was produced.

**Corrected: superlatives.** "Every existing RCA benchmark is cloud
microservices", "nobody has published a controlled comparison" and
"first-to-document" were unbounded claims. The first is contradicted by a 2024
LLM-agent diagnosis benchmark for AI clusters, and the second needed a caveat:
a 2026 comparison of Kueue, Volcano and Slinky exists, though not on identical
hardware. They are replaced by statements of what I searched for and did not
find, with the closest work cited.

**Corrected: dates.** The two January 2026 deep dives now carry the date they
were first committed to this site, and the KV-cache post cites the paper its
figures come from.

**Unpublished: the volatility-surface design page.** It had no code, unsourced
timing baselines, past-due milestones and two textbook errors. It is kept in
the repository as a draft.

If you find something else, [tell me](/contact/).
