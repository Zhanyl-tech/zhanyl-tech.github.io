---
layout: single
title: "Projects"
permalink: /projects/
author_profile: true
toc: true
toc_label: "Projects"
toc_icon: "code"
---

Building production-grade systems at the intersection of AI/ML, quantitative finance, and high-performance computing.

---

## <a name="defai"></a>🤖 DeFAI: Autonomous Trading Agent

**Status:** 🟢 Production (Paper Trading)  
**Timeline:** September 2024 - Present  
**GitHub:** [Private - Available upon request](mailto:your-email@example.com)

### Overview

Autonomous trading system that combines Large Language Model reasoning (GPT-4/Claude) with reinforcement learning to identify and execute DeFi arbitrage opportunities across multiple blockchains.

### Key Results

- **68% Win Rate** across 89 executed trades
- **1.4 Sharpe Ratio** with controlled risk exposure
- Processing **10M+ blockchain events daily** in real-time
- Sub-second decision latency for time-sensitive opportunities
- Automated position management with dynamic risk controls

### Technical Architecture

**AI/ML Components:**
- LLM-powered market analysis using GPT-4 and Claude 3.5
- Reinforcement learning for strategy optimization (PPO/A3C)
- Custom reward functions incorporating risk-adjusted returns
- Ensemble model for confidence scoring

**Infrastructure:**
- Python backend with FastAPI for real-time data processing
- Docker containerization with Kubernetes orchestration
- PostgreSQL + TimescaleDB for time-series market data
- Redis for low-latency caching and pub/sub messaging
- Real-time monitoring with Prometheus + Grafana

**Data Pipeline:**
- Multi-chain blockchain event monitoring (Ethereum, BSC, Polygon)
- WebSocket feeds for real-time price data
- Custom data normalization and feature engineering
- Backfill system for historical analysis

### Technical Highlights

```python
# Example: LLM-Powered Market Analysis Module
class MarketAnalysisAgent:
    def analyze_opportunity(self, market_data):
        # Combine quantitative signals with LLM reasoning
        quant_signals = self.calculate_technical_indicators(market_data)
        llm_analysis = self.llm.analyze(
            prompt=self.build_analysis_prompt(market_data, quant_signals),
            model="gpt-4"
        )
        confidence_score = self.ensemble_scoring(quant_signals, llm_analysis)
        return TradingSignal(confidence=confidence_score, reasoning=llm_analysis)
```

### Challenges Solved

- **Latency Optimization:** Reduced decision latency from 5s to <500ms through caching and async processing
- **False Positives:** Cut false signals by 40% using ensemble confidence scoring
- **Gas Fee Optimization:** Dynamic gas price prediction to maximize net returns
- **Chain Failures:** Robust retry logic with automatic fallback to backup RPC nodes

### Next Steps

- Expanding to 5+ additional chains (Arbitrum, Avalanche, Optimism)
- Advanced RL techniques (Multi-agent systems)
- Live trading deployment with $5K-10K capital (Q1 2026)

---

## <a name="cqf"></a>📊 Quantitative Finance Research (CQF)

**Status:** ✅ Completed (January 2026)  
**Timeline:** September 2025 - January 2026  
**GitHub:** [Private - Available upon request](mailto:your-email@example.com)

Four graduate-level quantitative finance projects demonstrating expertise in derivatives pricing, statistical modeling, and algorithmic trading.

### Project 1: Local Volatility Surface Calibration

**Objective:** Implement Dupire's local volatility model for accurate option pricing

**Technical Approach:**
- Calibrated local volatility surface from market option prices (S&P 500)
- Solved Dupire PDE using finite difference methods
- Validated against Black-Scholes and market prices

**Results:**
- **<2% pricing error** vs actual SPX option prices across strikes
- Successfully handled volatility smile and term structure
- Production-ready implementation in Python with QuantLib

**Tech Stack:** Python, NumPy, SciPy, QuantLib, Matplotlib

```python
# Local Vol Surface Calibration
def calibrate_local_vol_surface(market_prices, strikes, maturities):
    """
    Calibrate Dupire local volatility from market option prices
    """
    # Fit implied volatility surface
    impl_vol_surface = fit_implied_vol(market_prices, strikes, maturities)
    
    # Compute local volatility using Dupire formula
    local_vol_surface = dupire_local_vol(impl_vol_surface)
    
    return local_vol_surface
```

### Project 2: Statistical Arbitrage - Pairs Trading

**Objective:** Build cointegration-based pairs trading strategy

**Technical Approach:**
- Identified cointegrated stock pairs using Engle-Granger test
- Mean-reversion strategy with dynamic z-score thresholds
- Risk management with position sizing and stop-losses

**Results:**
- **12% annual return** on backtest (2020-2024 US equities)
- Sharpe ratio: **1.8**
- Maximum drawdown: **-8%**

**Tech Stack:** Python, Pandas, Statsmodels, Backtrader

### Project 3: Risk Management Framework

**Objective:** Implement comprehensive risk metrics for portfolio management

**Technical Implementation:**
- Value at Risk (VaR) using Historical, Parametric, and Monte Carlo methods
- Conditional Value at Risk (CVaR) for tail risk
- Stress testing under extreme market scenarios
- Portfolio optimization with risk constraints

**Results:**
- Accurate risk forecasting: 95% VaR predictions within 3% of realized losses
- Stress test framework identifying portfolio vulnerabilities
- Optimal portfolios with 20% lower volatility for same return

**Tech Stack:** Python, NumPy, SciPy, Pandas, Monte Carlo simulation

### Project 4: Algorithmic Trading - Execution Algorithms

**Objective:** Implement VWAP and TWAP execution algorithms with slippage minimization

**Technical Approach:**
- Volume-Weighted Average Price (VWAP) algorithm
- Time-Weighted Average Price (TWAP) with adaptive scheduling
- Smart order routing with liquidity detection
- Transaction cost analysis (TCA)

**Results:**
- **30% reduction in slippage** vs naive execution
- <5 basis points execution cost on liquid stocks
- Backtested on 1 year of high-frequency trade data

**Tech Stack:** Python, Pandas, Backtrader, Interactive Brokers API

---

## <a name="hpc"></a>⚡ HPC ML Inference Engine *(Planned)*

**Status:** 🔵 Design Phase  
**Timeline:** Q1 2026 - Q2 2026

### Objective

Build a distributed, high-performance ML inference system optimized for sub-millisecond latency in real-time trading applications.

### Planned Architecture

**Components:**
- C++/CUDA inference engine for GPU acceleration
- Model quantization (INT8/FP16) for faster inference
- Distributed serving with load balancing
- gRPC API for low-latency communication
- Model versioning and A/B testing framework

**Target Performance:**
- <1ms p99 latency for model inference
- 10,000+ requests/second throughput
- Horizontal scalability across GPU nodes
- 99.99% uptime SLA

**Tech Stack:** C++, CUDA, TensorRT, gRPC, Kubernetes, Prometheus

---

## 🔬 Additional Projects

### Distributed ML Training Platform *(Planned)*

**Objective:** Build distributed training infrastructure for large-scale ML models

**Key Features:**
- Multi-node distributed training (PyTorch DDP)
- Hyperparameter optimization at scale (Ray Tune)
- Experiment tracking and model registry (MLflow)
- Cost optimization for cloud GPU resources

**Status:** Design phase, targeting Q2 2026

---

## 📂 Open Source Contributions

Working on:
- Contributing to QuantLib (C++ quant finance library)
- PyTorch performance optimizations
- Trading system tooling and infrastructure

---

## 🛠️ Technical Skills

**Languages:** Python, C++, SQL, Bash, JavaScript  
**ML/AI:** PyTorch, TensorFlow, LangChain, scikit-learn, Transformers  
**Quant Finance:** QuantLib, NumPy, SciPy, Pandas, Statsmodels  
**Infrastructure:** Docker, Kubernetes, AWS, PostgreSQL, Redis, Kafka  
**Tools:** Git, Linux, CI/CD, Monitoring (Prometheus, Grafana)

---

## 📧 Collaboration

Interested in discussing any of these projects or collaborating on similar work? Reach out via [email](mailto:your-email@example.com) or [LinkedIn](https://linkedin.com/in/yourprofile).

<div style="text-align: center; margin: 2em 0;">
  <a href="/" class="btn btn--info">← Back Home</a>
  <a href="/blog/" class="btn btn--info">Read Blog →</a>
</div>

