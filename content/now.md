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

**[cluster-sre-agent](/projects/cluster-sre-agent/)**, phase 3 of 6. The
dependency graph and the read-only tool surface are built and tested; the LLM
configurations are next. The graph is the interesting part — 62% of its edges
are measured on a live cluster rather than assumed, and the load-bearing one
records that a stalled accounting path does *not* halt scheduling.

Next after that: **k8s-gpu-scheduler-lab**, a controlled comparison of
Kubernetes GPU schedulers on the same traces.

## Writing

Next post: what happened when I tried to reproduce the storage-stall-to-
scheduling-halt chain everyone repeats, and could not. It is the most useful
negative result I have measured this year.

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

*Last updated: 16 August 2026.*
