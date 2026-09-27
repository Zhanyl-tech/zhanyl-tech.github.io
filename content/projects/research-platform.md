---
title: "research-platform"
date: 2026-08-01
lastmod: 2026-09-26
description: "A point-in-time data layer for quantitative research: an append-only bitemporal store where every query takes an as-of date. Phase 1 of 6; feature lineage and leakage detection are planned."
summary: "A point-in-time data layer for quantitative research. Phase 1 of 6; feature lineage and leakage detection are planned."
tags: [python, quantitative-research, point-in-time, duckdb]
status: "Phase 1 of 6 · point-in-time store built · lineage, leakage detection planned"
stage: "partial"
group: "quant"
repo: "https://github.com/Zhanyl-tech/research-platform"
weight: 20
ShowToc: false
---

**[github.com/Zhanyl-tech/research-platform](https://github.com/Zhanyl-tech/research-platform)** · Python · MIT

<p class="project-status"><span class="status status-partial">partial</span>
Phase 1 of 6 is built: the point-in-time data layer. Feature lineage (phase 2),
the data-quality and leakage monitor (phase 3), experiment tracking, a
walk-forward evaluation harness and scale-out are <strong>planned, not
built</strong>. The reference data is a deterministic synthetic fixture.</p>

<!-- OWNER: this page describes the repository as of 2026-09-26; it was being
changed on its improve/2026-09 branch at the time. Re-check the wording after
that branch is merged. -->

You test a signal. It works. You put it into production and it does not.

Often nothing is wrong with the model. The database is a *current-state*
database, and it quietly told you things you could not have known: the revenue
figure was restated in November, your universe contains only companies that
survived, your prices are adjusted for splits that had not happened yet, and
the ticker `ZZZ` is two different companies spliced at the seam.

None of these throw an error. They produce a clean, plausible series and a
Sharpe ratio that does not survive contact with reality.

Every record here carries the date it became *knowable* separately from the
date it describes, nothing is overwritten (the API has no update or delete
path), and every query takes an as-of date. That makes this class of bug
structurally impossible rather than carefully avoided, with one precondition
the store cannot check for you: every source must stamp its knowledge dates
honestly.

`make demo` runs offline, with no credentials, and walks five traps
(survivorship, ticker recycling, a restatement, a corporate action, late data),
each showing the same query returning different and correct answers on
different as-of dates.

Phase 3's leakage detector is the reason for the order: it only means
something once the data layer can say what was knowable when.
