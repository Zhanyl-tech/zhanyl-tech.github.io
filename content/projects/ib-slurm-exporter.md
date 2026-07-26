---
title: "IB Slurm Exporter"
date: 2026-07-26
description: "Correlate InfiniBand and RoCE counters with the Slurm job that owns them, so a slow collective can be traced to the fabric."
summary: "Correlate InfiniBand and RoCE counters with the Slurm job that owns them, so a slow collective can be traced to the fabric."
tags: [slurm, infiniband, rdma, prometheus, golang]
status: "Shipped"
repo: "https://github.com/Zhanyl-tech/ib-slurm-exporter"
weight: 3
ShowToc: false
---

**[github.com/Zhanyl-tech/ib-slurm-exporter](https://github.com/Zhanyl-tech/ib-slurm-exporter)** · Go · MIT

```
make demo
```

No InfiniBand, no cluster, no Linux required — it builds a synthetic `/sys`,
`/proc` and cgroup tree and serves real metrics off it.

## The problem

A 64-node run drops from 4,200 to 900 samples/sec. GPUs look busy. Slurm says
`RUNNING`. Your Slurm exporter reports job count, state, and runtime — none of
which move.

The cause is one HCA retransmitting: `packet_seq_err` climbing on `mlx5_1`,
stalling the all-reduce and idling every GPU behind it.

Fabric monitoring can see that counter. It just cannot tell you *which job* owns
it, because nothing connects a Slurm job ID to a network device.

## The join

Neither Slurm nor the HCA knows about the other. The bridge turns out to be a
file descriptor — any process doing RDMA holds one open on a uverbs device:

```
job_918001/step_0/cgroup.procs → PID 41001
  → /proc/41001/fd/3 → /dev/infiniband/uverbs0
  → /sys/class/infiniband_verbs/uverbs0/ibdev → "mlx5_0"
  → /sys/class/infiniband/mlx5_0/ports/1/hw_counters/packet_seq_err
```

That last hop goes through sysfs on purpose. `uverbs3` does **not** have to mean
`mlx5_3` — the numbering is independent. A host where they happen to match is
exactly the host where the shortcut looks correct and is wrong somewhere else.

## What it refuses to do

**InfiniBand counters are per-device. The HCA counts packets; it has no idea
which process sent them.**

When two jobs share a node and both use `mlx5_1`, splitting `port_xmit_data`
between them is not hard — it's impossible. The information isn't in the
hardware.

Exporters that paper over this emit job-labelled series that are wrong in the
worst way: a noisy neighbour's retries land on a healthy job, so the metric
misleads you precisely when you're using it to debug an incident.

So there are two families. `ib_slurm_job_*` appears **only** when a job is the
device's sole user. `ib_slurm_device_*` always appears and is never
job-labelled. A third series, `ib_slurm_device_jobs`, shows *why* attribution is
missing instead of leaving a mysterious gap.

Suppressing attribution never loses data. In the demo `mlx5_1` is shared, and
its 48,221 `packet_seq_err` are still exported — at device level, where they're
true.

## Slurm 26.05 broke the usual approach

From the release notes:

> cgroup/v2 directory structures are now keyed off of SLUID and not the JobId.

Anything doing `Atoi` on the segment after `job_` now gets a parse error, or
worse, a number that isn't a job ID. Nothing errors at runtime. Series just stop
appearing, or appear against the wrong job.

All three layouts are handled — v1, v2, and 26.05's SLUID form. Identifiers are
treated as opaque; non-numeric ones resolve through `scontrol`, and anything
that fails to resolve is **counted, never guessed**. A metric on the wrong job is
worse than a metric on no job.

I found this while writing up the [25.11 vs 26.05
comparison](/experiments/2026-07-26-slurm-25-11-upgrade-notes/), which is the
only reason this tool handles it — the approach I'd sketched a day earlier was
already obsolete.

Worth knowing separately: PIDs live in the *step* cgroups, not the job-level
one. An exporter reading only `job_*/cgroup.procs` finds nothing and reports an
empty cluster.

## Honest caveat

The SLUID path is implemented from the release notes and has **not** been
validated against a live 26.05 cluster. If you run one, I'd like to know what
the real directory names look like.

## Design note

Every root — sysfs, proc, verbs, cgroup — is injectable. That's what lets a
Linux-only exporter be tested and demoed on a laptop, and it's why the 14 tests
run anywhere. It also means the synthetic tree is deliberately awkward: two jobs
share an HCA so the suppression path is exercised, and one allocation is keyed
by SLUID so the 26.05 layout is too.
