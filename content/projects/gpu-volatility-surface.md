---
draft: true  # Unpublished 2026-09-26: a design note with no code, past-due milestones and unsourced baseline timings. See the comment at the top of the body.
title: "GPU-Accelerated Volatility Surface Calibration"
date: 2026-01-01
description: "Design notes for GPU-accelerated local- and stochastic-volatility calibration. No public code."
tags: [quantitative-finance, cuda, gpu, volatility, derivatives]
summary: "Design notes for GPU-accelerated local- and stochastic-volatility calibration. No public code."
ShowToc: true
weight: 30
status: "No public code — design notes only"
stage: "planned"
group: "quant"
---

<!--
Unpublished (draft: true) on 2026-09-26, not deleted.

Why: the published page was essentially unverifiable claims. It has no public
repository; its CPU "baseline" timings (~30 s local vol, ~120 s for a 10K-path
Heston Monte Carlo, ~5 s SABR, "30-60 seconds" for an SPX surface) were not
measured and had no source; its milestones (M1 July 2026, M2 September 2026)
had passed unchecked; and it stated two textbook errors, corrected below:
Heston pricing does not require Monte Carlo (Heston 1993 is titled "A
Closed-Form Solution for Options with Stochastic Volatility..." and gives a
semi-closed-form solution through the characteristic function), and Dupire
local volatility is a pointwise formula, not something obtained "via a PDE".
It also sat in the homepage project list above shipped tools.

The unsourced timing table and the stale milestones have been removed below.

OWNER: to republish, (1) create the public repository, (2) replace the
milestones with dates you can commit to (or none), (3) publish a CPU baseline
only when it has been measured, with the command, hardware and library
versions that produced it, and (4) remove draft: true. The CQF project
references below are yours to confirm; they are unchanged.
-->

**Status: no public code — design notes only.** Nothing on this page has been
implemented or measured.

**Stack (planned):** CUDA · C++ · Python · QuantLib · NumPy · SciPy · Numba

---

## What This Is

GPU-accelerated calibration of volatility surfaces: fitting local and
stochastic volatility models to market option prices, fast enough to run
continuously as prices move.

## The Problem

Volatility surface calibration is a core operation on an options desk:

1. Take observed market option prices across strikes and maturities.
2. Fit a model (Dupire local vol, Heston stochastic vol, or SABR) to them.
3. Use the fitted surface to price exotics or hedge.
4. Repeat as prices update.

The goal is to make step 2 fast enough to run continuously. No CPU baseline
has been measured yet, so no speed-up is claimed here.

## Technical Approach

### Local volatility (Dupire)

Dupire's formula gives local volatility **pointwise** from derivatives of the
call-price surface with respect to maturity and strike (equivalently, from the
implied-volatility surface). Obtaining it is a formula evaluation, not a PDE
solve; the practical difficulty is that it differentiates noisy market data
twice in strike, so the input surface must be smoothed and arbitrage-free
first. A PDE (finite-difference) solver enters when *pricing* under the
calibrated local-vol model, and that grid evaluation is the part that maps
naturally onto a GPU.

### Heston stochastic volatility

Heston's model has a semi-closed-form price for European options through its
characteristic function (Heston, *A Closed-Form Solution for Options with
Stochastic Volatility with Applications to Bond and Currency Options*, Review
of Financial Studies 6(2), 1993). Calibration to vanilla prices therefore
normally uses Fourier-based pricing (numerical integration of the
characteristic function), not Monte Carlo. Monte Carlo is the tool for pricing
path-dependent exotics under the calibrated model; the GPU question is which of
the two dominates the workload.

### Optimisation loop

Both models need nonlinear least squares (for example Levenberg–Marquardt) to
fit parameters to market prices. The optimiser can stay on the CPU while the
inner pricing loop, evaluated across many strikes and maturities, runs on the
GPU.

## Connection to CQF Work

This was planned to build on CQF projects:
- Local vol calibration (Project 1)
- Risk management (Project 3), GPU-accelerated Monte Carlo for VaR

## Milestones

<!-- OWNER: the original milestones (M1 July 2026 CPU baseline, M2 September
2026 CUDA local-vol kernel, M3 October 2026, M4 November 2026 public repo)
had passed or were unconfirmed on 2026-09-26. Add dates only when you can
commit to them. -->

No dates are committed.
