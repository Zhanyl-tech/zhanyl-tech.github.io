---
title: "GPU-Accelerated Volatility Surface Calibration"
date: 2026-01-01
description: "CUDA-accelerated local and stochastic volatility surface calibration — Dupire's model, Heston, and hybrid approaches for real-time derivatives pricing."
tags: [quantitative-finance, cuda, gpu, volatility, derivatives, pricing, hpc]
summary: "Applying HPC and GPU computing to quantitative finance: calibrating volatility surfaces in real-time using CUDA kernels, finite difference methods, and Monte Carlo simulation."
ShowToc: true
weight: 3
status: "Design Phase"
---

**Status:** 🔵 Design phase — no public repository yet. Write-up only.  
**Stack:** CUDA · C++ · Python · QuantLib · NumPy · SciPy · Numba

---

## What This Is

GPU-accelerated calibration of volatility surfaces for real-time derivatives pricing. Specifically: taking the computationally expensive problem of fitting local and stochastic volatility models to market data, and making it fast enough to run continuously as markets move.

This project sits at the intersection of my two domains — HPC infrastructure and quantitative finance — and is the bridge between them.

## The Problem

Volatility surface calibration is a core operation in options trading desks. You need to:
1. Take observed market option prices across strikes and maturities
2. Fit a model (Dupire local vol, Heston stochastic vol, or SABR) to these prices
3. Use the fitted surface to price exotic options or hedge positions
4. Do this continuously as market prices update (ideally sub-second)

The calibration step — fitting the model — is where standard CPU implementations fall short. A full SPX volatility surface calibration can take 30-60 seconds on a single CPU core. That's fine for end-of-day batch processing. It's not fine for real-time trading.

**Goal:** <1 second for full surface recalibration using GPU parallelism.

## Why GPU Acceleration Works Here

Volatility surface calibration involves:
- Solving PDEs across a grid of (strike, maturity) points — embarrassingly parallel
- Monte Carlo simulation for exotic option pricing — thousands of independent paths
- Nonlinear optimization with many function evaluations — each evaluation is a grid computation

All three are naturally parallel. The CPU bottleneck is serialization, not compute. Moving to GPU eliminates that bottleneck.

## Planned Architecture

```
┌──────────────────────────────────────────────────────┐
│               Market Data Input                      │
│    SPX option chain · Bid/Ask · Strikes · Maturities │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│            Implied Vol Extraction (CPU)              │
│         Black-Scholes inversion · Interpolation      │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│          GPU Calibration Engine (CUDA)               │
├──────────────────┬───────────────────────────────────┤
│  Dupire Local    │  Heston Stochastic   │  SABR       │
│  Vol (PDE FDM)   │  Vol (MC paths)      │  (Analytic) │
│                  │                      │             │
│  CUDA kernel:    │  CUDA kernel:        │  Vectorized │
│  parallel grid   │  parallel path       │  CPU+GPU    │
│  evaluation      │  simulation          │             │
└──────────────────┴──────────────────────┴────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│              Calibrated Surface Output               │
│     Local Vol σ(K,T) · Stochastic Vol params         │
│     Pricing engine ready · Greeks computation        │
└──────────────────────────────────────────────────────┘
```

## Technical Approach

### Local Volatility (Dupire)
Dupire's formula gives the local volatility surface directly from the implied volatility surface via a PDE. The computation is a grid evaluation — each point on the (K,T) grid is independent. CUDA maps naturally: one thread per grid point.

### Heston Stochastic Volatility (Monte Carlo)
Heston requires Monte Carlo simulation for pricing: simulate thousands of paths of the underlying and variance process, compute payoffs, average. Classic GPU workload — each path is independent. Expecting 100-1000x speedup over single-core CPU.

### Optimization Loop (Levenberg-Marquardt)
Both models require nonlinear optimization to fit model parameters to market prices. Each objective function evaluation is a GPU kernel call. The optimization loop runs on CPU, but the expensive inner loop runs on GPU.

## Planned Benchmarks

| Model | Operation | CPU (single core) | GPU (A100) | Speedup |
|-------|-----------|-------------------|------------|---------|
| Local Vol (Dupire) | Surface calibration | ~30s | Target: <1s | 30x+ |
| Heston | 10K path MC | ~120s | Target: <2s | 60x+ |
| SABR | Surface fit | ~5s | Target: <0.2s | 25x+ |

## Connection to CQF Work

This builds directly on my CQF projects:
- Local vol calibration (Project 1) — production-grade this implementation
- Risk management (Project 3) — GPU-accelerated Monte Carlo for VaR
- The mathematical foundations are from CQF; the HPC implementation is the new contribution

## Milestones

- [ ] **M1** (July 2026): CPU baseline — clean Python implementation with QuantLib validation
- [ ] **M2** (September 2026): CUDA local vol kernel — first GPU implementation
- [ ] **M3** (October 2026): Heston Monte Carlo on GPU, benchmark vs CPU
- [ ] **M4** (November 2026): Full pipeline, benchmarks, public repo + writeup

## Related Posts

*Posts will appear here as they're published.*

---

*[GitHub: Available November 2026](https://github.com/Zhanyl-tech)*
