---
title: "About"
layout: "single"
url: "/about/"
summary: "I build the systems that allocate scarce, expensive, heterogeneous compute — and the benchmarks that prove whether they actually work."
ShowToc: false
---

I build the systems that allocate scarce, expensive, heterogeneous compute —
and the benchmarks that prove whether they actually work.

That sentence is deliberate. The tools change: Slurm today, Kubernetes next,
rack-scale disaggregated hardware after that. The problem doesn't. Somebody has
to decide which job gets which accelerator, prove the decision was right, and
diagnose it when the answer stops being obvious.

I'm a senior cluster engineer in platform engineering at a quantitative hedge
fund, working on the GPU compute platform behind machine-learning research.
Scheduling and fairshare policy, GPU lifecycle, distributed storage, and the
telemetry that turns "the cluster feels slow" into a number.

## What I actually work on

**Scheduling and resource allocation.** Multifactor priority, backfill,
fairshare decay, gang scheduling, preemption. I replay real job traces against
policy changes before they reach a controller, because the alternative is
finding out in production. The measured result that surprised me: backfill
moved CPU utilization from 72.2% to 83.6% and cut mean job wait from 1,913
minutes to 374, while the priority weights everyone tunes first barely
mattered.

**Measurement and honest evaluation.** Most infrastructure claims are folk
knowledge. I build benchmarks to check them, and I publish the ones that come
out negative — the first finding in my incident-diagnosis benchmark was that
its own flagship scenario doesn't happen the way everyone says it does.

**Agentic operations, carefully.** Published LLM agents reach roughly 49% on
the best root-cause-analysis benchmarks. That number should determine how much
autonomy you grant, and mostly it doesn't. I'm interested in the guardrails and
the calibration more than the agent.

## Background

Ten years of production infrastructure in financial services — quantitative
research computing, exchange platform engineering, Linux systems at fleet
scale. MS in Computer Science (machine learning) at Georgia Tech, the
Certificate in Quantitative Finance, and NVIDIA's NCP-AIO.

The combination is intentional. I want to build ML platforms for people doing
quantitative research, which means understanding the systems, the agents that
operate them, and the mathematics they run.

---

**Hiring, collaborating, or investing?** [Start here](/contact/) — tell me what you
have in mind and I'll send my CV if it's a fit.

**Elsewhere:** [GitHub](https://github.com/Zhanyl-tech) ·
[LinkedIn](https://www.linkedin.com/in/za-engineering/) ·
[X](https://x.com/ZhanylAbd) · [Now](/now/) · [RSS](/index.xml)
