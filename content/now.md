---
title: "Now"
layout: "single"
url: "/now/"
summary: "What I'm building, writing, learning and reading right now."
ShowToc: false
---

What I'm working on at the moment. Updated monthly — a
[now page](https://nownownow.com/about), not a changelog.

## Building

**[k8s-gpu-scheduler-lab](/projects/k8s-gpu-scheduler-lab/)**, phase 1 of 3,
now public. The kwok substrate, the workload generator, the metrics and the
degenerate baselines are built, and K0 — the default `kube-scheduler` — is
measured on a real control plane. Phase 2 is Kueue and Volcano, which is where
the comparison actually starts. The 34% bin-packing claim the repo exists to
test has not been tested yet, and its row stays empty until it has.

Also shipped this month: **[slurm-mcp](/projects/slurm-mcp/)** and
**[cluster-ops-skills](/projects/cluster-ops-skills/)** — the read-only tool
surface an agent reads a cluster through, and the runbooks it follows once it
can.

Still in flight: **[cluster-sre-agent](/projects/cluster-sre-agent/)**, phase 3
of 6. The dependency graph and read-only tool surface are built and tested; the
LLM configurations need an API key and are next. The graph is the interesting
part — 62% of its edges are measured on a live cluster rather than assumed.

## Writing

Next post: what happened when I tried to reproduce the storage-stall-to-
scheduling-halt chain everyone repeats, and could not. It is the most useful
negative result I have measured this year.

## Submitting

Talks and papers in flight, so there is one place to look rather than an
announcement after the fact.

**Nothing under review right now.** Two things are close enough to name:

- The Kubernetes GPU scheduler comparison, once phase 2 has Kueue and Volcano
  numbers against the same trace. A controlled cross-scheduler comparison is
  the kind of thing SUG or KubeCon exists for, and it is not worth submitting
  before there are real numbers in it.
- The storage-stall refutation — a negative result about a widely-repeated
  causal chain, which is a better lightning talk than a paper.

This section stays honest about the difference between *submitted*, *accepted*
and *thinking about it*. Anything listed here without a status is in the last
category.

## Learning

MS CS at Georgia Tech — machine learning specialisation. Alongside it, reading
Slurm's scheduler source rather than only its documentation, which is where the
difference between "documented" and "actually true" keeps turning up.

## Reading

*Advances in Financial Machine Learning* (López de Prado) — chapter 7 on
temporal separation and embargoes is doing real work in the evaluation harness
for [research-platform](/projects/research-platform/).

*Developing Time-Oriented Database Applications in SQL* (Snodgrass) — the
standard treatment of bitemporal modelling, and the reason the point-in-time
store looks the way it does.

---

*Last updated: 23 August 2026.*
