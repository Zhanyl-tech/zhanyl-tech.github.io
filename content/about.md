---
title: "About"
layout: "single"
url: "/about/"
summary: "I build the systems that allocate scarce, expensive, heterogeneous compute, and the benchmarks that check whether they work: GPU scheduling across Slurm and Kubernetes, GPU fleet health, and measured-versus-asserted evaluation."
description: "Zhanyl Abdybaeva: GPU scheduling across Slurm and Kubernetes (Slinky), GPU fleet-health automation, and benchmarks that separate what was measured from what was asserted."
ShowToc: false
---

I build the systems that allocate scarce, expensive, heterogeneous compute —
and the benchmarks that check whether they actually work.

That sentence is deliberate. The tools change: Slurm today, Kubernetes next to
it, rack-scale disaggregated hardware after that. The problem doesn't. Somebody
has to decide which job gets which accelerator, show the decision was right, and
diagnose it when the answer stops being obvious.

<!-- OWNER: the homepage used to say "a quantitative trading firm" and this page
"a quantitative hedge fund". This page's wording is kept and the homepage no
longer names the employer; confirm this is the description you want public. -->
I'm a senior cluster engineer in platform engineering at a quantitative hedge
fund, working on the GPU compute platform behind machine-learning research.
Scheduling and fairshare policy, GPU lifecycle, distributed storage, and the
telemetry that turns "the cluster feels slow" into a number.

## What the public work covers

Everything below links to a repository, and each project page says what is
built, partial or planned, and what it was tested against. None of it has run
on a production GPU cluster; where something was measured, the page says on
what.

**Scheduler evaluation across Slurm and Kubernetes.**
[slurm-scheduler-lab](/projects/slurm-scheduler-lab/) is a discrete-event
model of Slurm's multifactor priority, Fair Tree fairshare and backfill that
reads a real `slurm.conf` and replays `sacct` traces.
[k8s-gpu-scheduler-lab](/projects/k8s-gpu-scheduler-lab/) runs the same kind of
workload against a real Kubernetes control plane with simulated GPU nodes
(kind + kwok): the default scheduler and four degenerate baselines are built,
Kueue, Volcano and NVIDIA KAI are not yet. On the simulator's synthetic
workload, backfill cut mean wait by a median 3.8× across 20 seeds; an extreme
job-size priority weight moved it by a comparable amount. An earlier version of
this page reported one seed of that workload as a measured result on real
traces; it was neither, and the [correction](/corrections/) says so.

**Slurm on Kubernetes.** [slinky-gitops](/projects/slinky-gitops/) brings up
Slurm 26.05 on kind with SchedMD's Slinky operator and tries to rotate the
cluster's auth key. The rotation does not currently work on Slinky v1.2, and
the script proves that by hashing the key inside every slurmd pod and rolling
back, rather than reporting success on a cluster that cannot run a job.

**GPU fleet health.** Three Go tools built on one rule, never act on absent
evidence: [epilog-gpu-validator](/projects/epilog-gpu-validator/) (drain a node
for a persistent GPU fault between jobs, never for a failed query that carries
no fault evidence), [gpu-reaper](/projects/gpu-reaper/) (find
allocated-but-idle GPUs, observe by default) and
[ib-slurm-exporter](/projects/ib-slurm-exporter/) (attribute InfiniBand/RoCE
counters to the job that owns them, and refuse when it can see that a port is
shared). All three are tested against simulators and synthetic trees, not
hardware.

**Measurement and honest evaluation.** Most infrastructure claims are folk
knowledge. I build benchmarks to check them, and I publish the ones that come
out negative. The first finding of my incident-diagnosis benchmark,
[slurm-rca-bench](/projects/slurm-rca-bench/), was that its own flagship
scenario does not happen the way it is usually told: with the accounting
database frozen on a Docker test cluster, scheduling carried on.

**Agentic operations, carefully.** Published LLM agents are still far from
dependable at root-cause analysis: on ORCA-bench (July 2026, 884 incident
tasks) the best strict RCA accuracy is 30.6% and the best partial-credit "RCA
depth" is 48.8%
([arXiv:2607.28545](https://arxiv.org/abs/2607.28545)). That gap should decide
how much autonomy an agent gets, so I am more interested in the guardrails and
the calibration than in the agent: a read-only tool surface enforced in code
([slurm-mcp](/projects/slurm-mcp/)) and an explicit failure-propagation graph
([cluster-sre-agent](/projects/cluster-sre-agent/)). No agent has been scored
yet.

## Background

Ten years of production infrastructure in financial services — quantitative
research computing, exchange platform engineering, Linux systems at fleet
scale. MS in Computer Science (machine learning) at Georgia Tech, the
Certificate in Quantitative Finance, and NVIDIA's NCP-AIO.

The combination is intentional. I want to build ML platforms for people doing
quantitative research, which means understanding the systems, the agents that
operate them, and the mathematics they run. The quantitative side of the work
is [research-platform](/projects/research-platform/), a point-in-time data
layer for backtesting.

---

**Hiring or collaborating?** [Start here](/contact/) — tell me what you have in
mind and I'll send my CV if it's a fit.

**Elsewhere:** [GitHub](https://github.com/Zhanyl-tech) ·
[LinkedIn](https://www.linkedin.com/in/za-engineering/) ·
[X](https://x.com/ZhanylAbd) · [Now](/now/) · [Corrections](/corrections/) ·
[RSS](/index.xml)
