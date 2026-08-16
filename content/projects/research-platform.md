---
title: "research-platform"
date: 2026-08-01
description: "Point-in-time data semantics for quantitative research — as-of queries, feature lineage, and leakage detection."
summary: "Point-in-time data semantics for quantitative research — as-of queries, feature lineage, and leakage detection."
tags: [python, quantitative-research, point-in-time, data-quality, mlops]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/research-platform"
weight: 9
ShowToc: false
---

**[github.com/Zhanyl-tech/research-platform](https://github.com/Zhanyl-tech/research-platform)** · Python · MIT

You test a signal. It works. You put it into production and it does not.

Often nothing is wrong with the model. The database is a *current-state*
database, and it quietly told you things you could not have known: the revenue
figure was restated in November, your universe contains only companies that
survived, your prices are adjusted for splits that had not happened yet, and
the ticker `ZZZ` is two different companies spliced at the seam.

None of these throw an error. They produce a clean, plausible series and a
Sharpe ratio that does not survive contact with reality.

Every record here carries the date it became *knowable* separately from the
date it describes, nothing is ever overwritten, and every query takes an as-of
date — which makes that class of bug structurally impossible rather than
carefully avoided.

`make demo` runs in about three seconds with no network and no credentials, and
walks five traps, each showing the same query returning different and correct
answers on different dates.
