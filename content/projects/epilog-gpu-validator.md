---
title: "Epilog GPU Validator"
date: 2026-07-26
lastmod: 2026-09-27
description: "A Slurm Epilog check of the GPUs a job just used: it drains a node on evidence of a persistent GPU fault, and never on a failed query without fault evidence or on a transient condition."
summary: "A Slurm Epilog check that drains a node for evidence of a persistent GPU fault, and never for a failed query without fault evidence or a transient condition."
tags: [slurm, gpu, nvidia, epilog, golang]
status: "Simulator-tested · not validated on GPU hardware"
stage: "built"
repo: "https://github.com/Zhanyl-tech/epilog-gpu-validator"
weight: 4
ShowToc: true
---

**[github.com/Zhanyl-tech/epilog-gpu-validator](https://github.com/Zhanyl-tech/epilog-gpu-validator)** · Go · MIT

<p class="project-status"><span class="status status-built">built</span>
Exercised against a simulator, synthetic <code>nvidia-smi</code> output and
fake <code>scontrol</code>/<code>nvidia-smi</code> binaries. <strong>No GPU and
no Slurm cluster were used.</strong> Where it relies on NVIDIA or Slurm
behaviour it cites the documentation, and the README lists the assumptions
still unverified. Report-only is the default.</p>

<!-- OWNER: this page describes the repository's improve/2026-09 branch as of
2026-09-26. Merge or push it before publishing. -->

```
make scenarios
```

Every case runs the real decision code with `--enforce` against a simulated
`nvidia-smi` and a stand-in `scontrol` that only records calls. Output of
`--scenario-table` on 2026-09-27:

```
CASE                                       STATUS            WORST     EXIT DETAIL
----------------------------------------------------------------------------------------------------------------------
healthy                                    ok                unknown   0    pcie-gen:gpu0,gpu1
pcie-degraded                              ok                unknown   0    pcie-gen:gpu0,gpu1 pcie-width:gpu0
remap-pending                              ok                transient 0    row-remap-pending:gpu0 row-remap-uncorrectable:gpu0
thermal                                    ok                transient 0    throttle:gpu0
ecc-na                                     ok                unknown   0    pcie-gen:gpu0,gpu1 unreadable:gpu0
no-persistence                             ok                unknown   0    ecc-volatile-unreliable:gpu0 pcie-gen:gpu0,gpu1
no-driver                                  not-checked       unknown   0    query-failed:node
hw-slowdown                                drained           degraded  1    epilog-gpu-validator degraded: throttle:gpu0
leaked-memory                              drained           degraded  1    epilog-gpu-validator degraded: leaked-memory:gpu0
ecc                                        drained           fatal     1    epilog-gpu-validator fatal: ecc-uncorrectable:gpu0
remap-failure                              drained           fatal     1    epilog-gpu-validator fatal: row-remap-failure:gpu0
off-bus                                    drained           fatal     1    epilog-gpu-validator fatal: nvidia-smi-exit-15:node
leaked-memory --shared-gpus                ok                unknown   0    leaked-memory:gpu0 pcie-gen:gpu0,gpu1
pcie-degraded --drain-on-pcie-width        drained           degraded  1    epilog-gpu-validator degraded: pcie-width:gpu0
ecc, minors reversed                       not-checked       unknown   0    gpu-number-ambiguous:slurm-gpu0,slurm-gpu1
ecc, minors reversed --gpu-numbering nvml  drained           fatal     1    epilog-gpu-validator fatal: ecc-uncorrectable:gpu0
ecc, minors reversed --gpu-numbering minor ok                unknown   0    pcie-gen:gpu2,gpu3
ecc, minors reversed, env_uuid             drained           fatal     1    epilog-gpu-validator fatal: ecc-uncorrectable:gpu0
job GPU missing from output                partially-checked unknown   0    not-in-output:slurm-gpu1 pcie-gen:gpu0
ecc, scontrol group-writable               drain-failed      fatal     1    epilog-gpu-validator fatal: ecc-uncorrectable:gpu0
no GPUs in env                             no-gpus           ok        0    -
GPU vars disagree                          not-checked       unknown   0    gpu-set-ambiguous:node
nvidia-smi absent                          config-error      unknown   0    --nvidia-smi: /usr/bin/nvidia-smi: no such file or directory
flag typo --budget 20                      config-error      unknown   0    bad command line: invalid value "20" for flag -budget: parse error
unknown flag                               config-error      unknown   0    bad command line: flag provided but not defined: -no-such-flag
```

These rows show how the simulator is modelled, not hardware results: the
simulated `nvidia-smi` output was written from NVIDIA's documentation, not
captured from a GPU. The simulated job holds Slurm GPUs 0 and 1, and every
fault is placed on `nvidia-smi`'s `gpu0`; the `minors reversed` rows number the
device files in reverse PCI order to show what each `--gpu-numbering` value
(below) does with that. A test (`TestREADMEScenarioTableIsCurrent`) compares the
README's copy of this table with the command's output byte for byte, so it
cannot drift silently.

## The problem

A GPU develops a fault mid-job. The job fails or, worse, silently returns wrong
numbers. Slurm marks the node idle. The next job lands on the same card and
fails the same way. Slurm provides the hooks for a health check but not the
check: the Epilog runs on every job completion, on the node, as root.

![Decision tree: a failed or unreadable GPU query exits zero and keeps the node in service; evidence of a persistent hardware fault exits non-zero and drains, and only with --enforce](/images/diagrams/epilog-severity.svg)

## Why it is a dangerous tool to write

**Slurm drains the node when the Epilog exits non-zero** ("If the Epilog fails
(returns a non-zero exit code), this will result in the node being set to a
DRAIN state", [prolog/epilog guide](https://slurm.schedmd.com/prolog_epilog.html)).
So a false positive does not produce a bad metric; it removes a working node,
and a fleet-wide cause removes every node, one job completion at a time.

That is not hypothetical. An audit of version 0.1.0 found two fleet-wide
problems in it. NVIDIA documents that an idle GPU's PCIe link "may be reduced
when the GPU is not in use", and 0.1.0 drained on a generation below maximum,
so on hardware that does this every node would drain after its next job (the
audit reproduced it with a synthetic idle row, not on a GPU). And the Epilog
runs with no `PATH`, so 0.1.0 never found `nvidia-smi` and silently checked
nothing. Both are fixed. Three rules follow:

1. **Never drain on ignorance.** A missing, timed-out or unparseable
   `nvidia-smi`, or a field reported as `[N/A]`, is a monitoring failure: exit
   0, loudly logged. Only four documented `nvidia-smi` exit codes (8, 10, 14,
   15) count as hardware evidence.
2. **Separate persistent faults from conditions that clear.** Uncorrectable ECC
   since the last driver load and a row-remapping failure are fatal; a hard
   thermal slowdown or power brake on an *idle* GPU, or memory still held after
   teardown, is degraded; thermal throttling, a pending row remap and rows
   already remapped are transient, and so is uncorrectable ECC seen only in the
   lifetime count, but only when persistence mode is on (otherwise it is
   unknown); a PCIe link below maximum is unknown, because NVIDIA documents that
   it "may be reduced when the GPU is not in use".
3. **Only one exit is non-zero**: a degraded or fatal finding, with
   `--enforce`, on a real run. Misconfiguration, an ambiguous GPU set and a
   failed query without one of those four exit codes all exit 0, and all log
   at error level.

Volatile versus aggregate ECC is the distinction worth labouring: volatile
counters reset when the driver unloads, and the driver unloads when no clients
remain unless persistence mode is on, so a zero volatile count at Epilog time
proves nothing without it, and the tool says so.

## Only the job's own GPUs

On a shared node, checking every GPU means a neighbour's faulty card drains the
node for a job that never touched it. So the tool checks only the GPUs the
Epilog environment names (`CUDA_VISIBLE_DEVICES`, `SLURM_JOB_GPUS`,
`GPU_DEVICE_ORDINAL`; if more than one is set they must agree), and checks
**nothing** it cannot tie to the job without guessing.

Those variables hold Slurm's own GPU index (established from Slurm's source;
the documentation does not say), and which GPU that index means depends on
gres.conf:
`nvidia-smi`'s number with `AutoDetect=nvml`, the `N` in `/dev/nvidiaN`
without it. `--gpu-numbering` says which applies. The default, `auto`, checks
a numbered GPU only where the two agree on this node (device minors in PCI bus
order) and otherwise reports it unchecked; `nvml`, `minor` and `uuid` state the
mapping, and `--check-config` fails on a node where `auto` would check nothing.
With gres.conf `Flags=env_uuid` (Slurm 26.05 and later) the job's GPUs arrive
as UUIDs, which name one device whatever the numbering. The one node-wide
signal is a documented hardware-fault exit code from `nvidia-smi`, such as a
GPU that has fallen off the bus.

## What it deliberately does not do

- **No load test.** An active test catches faults a passive query cannot, but
  the Epilog's time budget is short, and a killed Epilog drains the node for a
  check that never concluded. DCGM diagnostics or a periodic drain-and-test job
  are the right home for that.
- **No Xid parsing, no MIG, no history.** Each run is one snapshot; MIG devices
  are reported and not checked.
- **Never un-drains.** Bringing a node back is a human decision.
- **Under Slinky** (slurmd in a container) it is untested; the README lists
  what must hold inside the container first.

## The set

One of three fleet tools with one rule, **never act on absent evidence**:
[gpu-reaper](/projects/gpu-reaper/) treats a telemetry gap as a collector fault
rather than idleness, [ib-slurm-exporter](/projects/ib-slurm-exporter/) refuses
to attribute a port it can see is shared, and this exits clean when it cannot
see the hardware.
