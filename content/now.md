---
title: "Now"
layout: "single"
url: "/now/"
summary: "What I'm building, writing, learning and reading right now."
ShowToc: false
---

What I'm working on at the moment. A
[now page](https://nownownow.com/about), not a changelog.

## Building

**[k8s-gpu-scheduler-lab](/projects/k8s-gpu-scheduler-lab/)**, phase 2 of 3,
in progress. Phase 1 built the kwok substrate, the workload generator, the
metrics, the degenerate baselines and K0, the default `kube-scheduler`, measured
on a real control plane. Phase 2 so far is the measurement machinery Phase 1
showed was missing: repeated runs with spreads, a bootstrap screen for
differences, kube-scheduler queue parity for the baselines, time-scaled
controller settings, and a preemption baseline. It is built and tested, and has
**not** been run on a cluster yet, so every cluster number in the repository is
still Phase 1's. Kueue, Volcano and NVIDIA KAI are not built.

The comparison the repo was started for is NVIDIA's report that adding
bin-packing to the Volcano scheduler reduced GPU fragmentation on one
production cluster. The primary source,
[NVIDIA's technical blog (2025-03-31)](https://developer.nvidia.com/blog/practical-tips-for-preventing-gpu-fragmentation-for-volcano-scheduler/),
reports nodes with all four GPUs free going from 18 to 214 and utilisation of
roughly 90%. It gives no percentage reduction in fragmentation. The "34%
reduction, presented at KubeCon EU 2026" figure I started from is
**unverified**: I found it only in a
[third-party blog post](https://devops.gheware.com/blog/posts/top-kubernetes-integrations-ai-gpu-acceleration-2026.html)
that names no talk or speaker, and NVIDIA's post does not mention KubeCon. It
has not been tested here either way.

On the Slurm side, **[slurm-scheduler-lab](/projects/slurm-scheduler-lab/)**
now models Slurm's conservative backfill, Fair Tree fairshare and preemption,
reports spreads over seeds, and can replay a k8s-lab trace as the Slurm
control (S0) for that comparison, as a model only.

Still in flight: **[cluster-sre-agent](/projects/cluster-sre-agent/)**. The
dependency graph and the read-only tool surface are built and tested; the LLM
configurations are not. The graph has 12 edges, 4 of them measured on the
benchmark's Docker test cluster (`csa stats`). Three edges that used to be
labelled measured had no recorded run behind them and were relabelled; an
earlier version of this page said 62%.

**[slurm-mcp](/projects/slurm-mcp/)** and
**[cluster-ops-skills](/projects/cluster-ops-skills/)** — the read-only tool
surface an agent reads a cluster through, and the runbooks it follows once it
can — are public.

## Writing

<!-- OWNER: this section promised "Next post: the storage-stall refutation" on
23 August; it had not appeared by 26 September. Keep, date or drop it. -->
Planned, not scheduled: what happened when I tried to reproduce the
storage-stall-to-scheduling-halt chain everyone repeats, and could not.

This month's writing was corrections: the
[backfill write-up](/experiments/2026-07-26-slurm-backfill-time-limits/) and
the [Slurm upgrade note](/experiments/2026-07-26-slurm-25-11-upgrade-notes/)
were both wrong in ways worth reading, and one set of inference numbers was
withdrawn. All of it is on [corrections](/corrections/).

## Submitting

Talks and papers in flight, so there is one place to look rather than an
announcement after the fact.

**Nothing under review right now.** Two things are close enough to name:

- The Kubernetes GPU scheduler comparison, once it has Kueue and Volcano
  numbers against the same trace (neither is built yet). A controlled cross-scheduler comparison is
  the kind of thing the Slurm User Group or KubeCon exists for, and it is not
  worth submitting before there are real numbers in it.
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
temporal separation and embargoes is shaping the evaluation harness planned for
[research-platform](/projects/research-platform/) (phase 5; not built yet).

*Developing Time-Oriented Database Applications in SQL* (Snodgrass) — the
standard treatment of bitemporal modelling, and the reason the point-in-time
store looks the way it does.

---

*Building, Writing and Reading updated 26 September 2026 to match the
repositories (Reading had implied that research-platform's evaluation harness
exists; it is planned), and Building again on 27 September to cite the source
of the 34% figure. Submitting was last changed on 27 September, to stop tying
the Kueue and Volcano numbers to a phase the repository does not assign them
to. Learning was last updated 23 August 2026.*
