---
title: "IB Slurm Exporter"
date: 2026-07-26
lastmod: 2026-09-27
description: "A Prometheus exporter that attributes InfiniBand and RoCE counters to the Slurm job using the HCA, refuses to attribute a port it can see is shared, and handles Slurm 26.05's SLUID cgroup layout."
summary: "Attribute InfiniBand and RoCE counters to the Slurm job using the HCA, and refuse to attribute a port it can see is shared."
tags: [slurm, infiniband, rdma, prometheus, golang]
status: "Synthetic /sys, /proc and cgroup trees only · not hardware"
stage: "built"
repo: "https://github.com/Zhanyl-tech/ib-slurm-exporter"
weight: 6
ShowToc: true
---

**[github.com/Zhanyl-tech/ib-slurm-exporter](https://github.com/Zhanyl-tech/ib-slurm-exporter)** · Go · MIT

<p class="project-status"><span class="status status-built">built</span>
Validated only against synthetic <code>/sys</code>, <code>/proc</code> and
cgroup trees built from the kernel and Slurm documentation. <strong>Not run on
InfiniBand hardware or on a Slurm 26.05 node.</strong> The packaging (systemd
unit, DaemonSet, container image) has not been run on a real host either.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26. Merge or push it before publishing. -->

```
make demo
```

No InfiniBand, no cluster, no Linux required: it builds a synthetic `/sys`,
`/proc` and cgroup tree and serves real metrics off it.

## The problem

*An illustrative scenario, not a measured incident:* a 64-node training run
drops from 4,200 to 900 samples/sec. GPUs look busy, Slurm says `RUNNING`, and
a Slurm exporter's job count, state and runtime do not move. The cause is one
HCA retransmitting — `packet_seq_err` climbing on `mlx5_1` — stalling the
all-reduce and idling every GPU behind it. Fabric monitoring can see that
counter; what it usually cannot tell you is which job on a shared compute node
was using that HCA.

![Five-hop chain from a Slurm cgroup through a PID and an open uverbs file descriptor to the per-port hardware counter](/images/diagrams/ib-join-chain.svg)

## The join

Neither Slurm nor the HCA knows about the other. By default the bridge is a
file descriptor: a process doing RDMA through libibverbs holds one open on a
uverbs device.

```
<scope>/<job>/step_0/user/task_0/cgroup.procs → PID 41001
  → /proc/41001/fd/3 → /dev/infiniband/uverbs0
  → /sys/class/infiniband_verbs/uverbs0/ibdev → "mlx5_0"
  → /sys/class/infiniband/mlx5_0/ports/1/hw_counters/packet_seq_err
```

The last hop goes through sysfs on purpose. `uverbs3` does **not** have to mean
`mlx5_3`; the numbering is independent, and a host where they happen to match
is exactly the host where the shortcut looks correct and is wrong elsewhere.

An opt-in second mode reads queue-pair ownership from the kernel's RDMA
resource tracking instead, which attributes per port and counts kernel RDMA
users (NFS/RDMA, Lustre o2ib, IPoIB) that the fd mode is blind to. It has a
blind spot of its own, listed below. Its key names come from iproute2's source;
it has not been run on hardware.

## What it refuses to do

Port counters are per port. The HCA counts packets; the counters do not record
which process sent them. When two jobs share `mlx5_1`, splitting its
`port_xmit_data` between them is not hard, it is impossible. Exporters that
paper over this put a noisy neighbour's retries on a healthy job, and mislead
you exactly when you are debugging with them.

So there are two families. `ib_slurm_job_*` appears **only** for a port whose
sole visible user is that job, and accumulates only the increase seen while it
was the sole user, so a visible neighbour's traffic never lands in it.
`ib_slurm_device_*` always appears and carries no job label. Anything that
leaves the user set incomplete (unreadable `/proc`, an unresolved SLUID, a
failed QP listing) suppresses all job attribution for that sample and is
exported as a metric of its own. In the demo `mlx5_1` is shared: the synthetic
fixture starts it at 48,221 `packet_seq_err` and keeps it climbing, and that
count is still exported, at device level, where it is true.

## Slurm 26.05 changed the cgroup layout

From the [26.05 release notes](https://slurm.schedmd.com/release_notes.html)
(read 2026-09-27): "cgroup/v2 directory structures are now keyed off of SLUID
and not the JobId." With `cgroup.conf`'s `CgroupJobIdPaths` at its default
(`no`), the job directory is the bare SLUID, such as `sEKNKTV3WPV500`,
with no `job_` prefix ([cgroup.conf](https://slurm.schedmd.com/cgroup.conf.html)).
Version 0.1.0 of this exporter assumed `job_<SLUID>` and would have found no
jobs at all on such a node. All three layouts (cgroup v1, v2 by job ID, v2 by
SLUID) are now handled; a SLUID is resolved from the job's slurmstepd process
title or from `squeue`, and anything unresolved is counted, never guessed. That
handling is implemented from the documentation and tested on synthetic trees,
not on a live 26.05 node.

## Limitations

- **Never run on InfiniBand hardware.**
- **Ports it can see are shared are never job-attributed**, by design; in fd
  mode, where NCCL opens every active HCA, per-job attribution in practice
  needs node-exclusive jobs.
- **"Sole user" means sole *visible* user.** In the default fd mode, kernel
  RDMA users (IPoIB, NFS/RDMA, Lustre o2ib) are invisible, so their traffic can
  land on a job that looks like the only user; in qp mode, userspace queue
  pairs created through mlx5 DEVX (UCX's default on mlx5) are invisible. The
  README's ownership table lists each case.
- **No per-QP counter binding yet.** Binding the mlx5 retry counters per
  process would turn suppression into real per-job attribution for that
  signal; it is the next milestone.
- **mlx5-centric** hardware counters; RoCE PFC pause counters are netdev
  counters and are not collected.
- **Endpoint symptoms only.** An HCA counter says something on the path is
  dropping or reordering, not which link; pair it with a switch-side exporter.
