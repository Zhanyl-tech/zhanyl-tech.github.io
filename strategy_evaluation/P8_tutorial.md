# P8 Strategy Evaluation — Complete Tutorial & Implementation Guide

> **CS 7646 ML for Trading | Georgia Tech MSCS**  
> Symbol: `JPM` | In-sample: 2008-01-01–2009-12-31 | Out-of-sample: 2010-01-01–2011-12-31

---

## 0. Project Architecture at a Glance

```
strategy_evaluation/
├── indicators.py          ← P6 indicators (BBP, RSI, MACD, Momentum, Stoch%K) — shared
├── marketsimcode.py       ← portfolio valuation engine
├── RTLearner.py           ← Random Tree (P3) — base learner
├── BagLearner.py          ← Ensemble wrapper (P3) — Random Forest
├── QLearner.py            ← Q-Learner (P7) — optional if using RL path
├── ManualStrategy.py      ← Rule-based trader using 3+ indicators  ← YOU WRITE
├── StrategyLearner.py     ← ML-based trader wrapping BagLearner    ← YOU WRITE
├── experiment1.py         ← Manual vs StrategyLearner comparison   ← YOU WRITE
├── experiment2.py         ← Impact sensitivity analysis            ← YOU WRITE
├── testproject.py         ← Single entry point for all charts      ← YOU WRITE
└── grade_strategy_learner.py  ← provided autograder (do not edit)
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ML4T Data Pipeline                           │
│                                                                     │
│  util.get_data()  ──►  prices_df  ──►  indicators.py               │
│                                           │                         │
│                         ┌─────────────────┼───────────────────┐    │
│                         ▼                 ▼                   ▼    │
│                        BBP              RSI              MACD Hist  │
│                          └──────────────┬─────────────────┘        │
│                                         ▼                           │
│                              feature_matrix (N×3)                   │
│                                         │                           │
│                    ┌────────────────────┴─────────────────────┐    │
│                    ▼                                           ▼    │
│           ManualStrategy                             StrategyLearner│
│           (threshold rules)                     (BagLearner+RTLearner)│
│                    │                                           │    │
│                    └──────────┬────────────────────────────────┘    │
│                               ▼                                     │
│                       df_trades  (±1000, ±2000, 0)                  │
│                               │                                     │
│                               ▼                                     │
│                    marketsimcode.compute_portvals()                 │
│                               │                                     │
│                               ▼                                     │
│                     portfolio_value series                          │
│                    ┌──────────┴────────────┐                        │
│                    ▼                       ▼                        │
│             experiment1.py          experiment2.py                  │
│             (compare strategies)    (impact analysis)              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Indicators Deep Dive

You have **5 indicators from P6**. You must use at least 3 in both ManualStrategy and StrategyLearner. We will use **BBP, RSI, and MACD Histogram** as the primary three.

### 1.1 Bollinger Band %B (BBP)

**Intuition:** Where is the current price *within* the Bollinger Bands envelope?

\[
\text{BBP} = \frac{P_t - \text{Lower}_t}{\text{Upper}_t - \text{Lower}_t}
\]

where:
\[
\text{SMA}_t = \frac{1}{n}\sum_{i=0}^{n-1} P_{t-i}, \quad
\sigma_t = \text{std}(P_{t-n+1}, \ldots, P_t)
\]
\[
\text{Upper}_t = \text{SMA}_t + 2\sigma_t, \quad \text{Lower}_t = \text{SMA}_t - 2\sigma_t
\]

| BBP value | Interpretation |
|-----------|---------------|
| BBP > 1.0 | Price above upper band → **overbought** → SHORT signal |
| BBP < 0.0 | Price below lower band → **oversold** → LONG signal |
| 0 < BBP < 1 | Within bands → no signal |

**Parameters:** `window=20` (standard), tunable in StrategyLearner.

```python
def bbp(price, window=20):
    sma   = price.rolling(window).mean()
    std   = price.rolling(window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return (price - lower) / (upper - lower)   # single scalar array ✓
```

---

### 1.2 Relative Strength Index (RSI)

**Intuition:** Momentum oscillator measuring the speed and magnitude of price changes. Normalized to [0, 100].

\[
\text{RSI} = 100 - \frac{100}{1 + \text{RS}}, \quad \text{RS} = \frac{\text{Avg Gain}_{n}}{\text{Avg Loss}_{n}}
\]

where average gain/loss use Wilder's smoothed rolling mean over `n` periods.

| RSI value | Interpretation |
|-----------|---------------|
| RSI > 70  | **Overbought** → SHORT signal |
| RSI < 30  | **Oversold** → LONG signal |

**Parameters:** `window=14` (Wilder standard).

```python
def rsi(price, window=14):
    delta = price.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window).mean()
    rs    = gain / loss
    return 100.0 - 100.0 / (1.0 + rs)          # single scalar array ✓
```

---

### 1.3 MACD Histogram

**Intuition:** Captures the divergence between short-term and long-term momentum. The histogram shows when momentum is accelerating or decelerating.

\[
\text{EMA}_{\text{fast}} = \text{EWM}(P, \text{span}=12), \quad
\text{EMA}_{\text{slow}} = \text{EWM}(P, \text{span}=26)
\]
\[
\text{MACD} = \text{EMA}_{\text{fast}} - \text{EMA}_{\text{slow}}
\]
\[
\text{Signal} = \text{EWM}(\text{MACD}, \text{span}=9)
\]
\[
\text{Histogram} = \text{MACD} - \text{Signal}
\]

| Histogram | Interpretation |
|-----------|---------------|
| Histogram > 0 and rising | Bullish momentum → LONG signal |
| Histogram < 0 and falling | Bearish momentum → SHORT signal |
| Zero crossing (−→+) | Momentum flip → consider LONG |
| Zero crossing (+→−) | Momentum flip → consider SHORT |

```python
def macd_histogram(price, fast=12, slow=26, signal=9):
    ema_fast   = price.ewm(span=fast, adjust=False).mean()
    ema_slow   = price.ewm(span=slow, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line              # single scalar array ✓
```

---

### 1.4 Momentum (reference — optional 4th indicator)

\[
\text{Momentum}_t = \frac{P_t}{P_{t-n}} - 1
\]

Positive momentum → trend continuation → LONG; negative → SHORT.

---

### 1.5 Stochastic %K (reference — optional 5th indicator)

\[
\%K_t = \frac{P_t - \text{Low}_{n,t}}{\text{High}_{n,t} - \text{Low}_{n,t}} \times 100
\]

%K > 80 → overbought; %K < 20 → oversold.

---

## 2. Manual Strategy — Design

### 2.1 Signal Logic

We combine **3 indicators** into a single position signal using a **vote / threshold system**:

```
For each trading day t:

  score = 0

  if BBP(t) < 0.0:      score += 1    # oversold → bullish
  if BBP(t) > 1.0:      score -= 1    # overbought → bearish

  if RSI(t) < 30:       score += 1    # oversold → bullish
  if RSI(t) > 70:       score -= 1    # overbought → bearish

  if MACD_hist(t) > 0 and MACD_hist(t-1) <= 0:  score += 1   # bullish cross
  if MACD_hist(t) < 0 and MACD_hist(t-1) >= 0:  score -= 1   # bearish cross

  if   score >=  2:  target_position = +1000   (LONG)
  elif score <= -2:  target_position = -1000   (SHORT)
  else:              target_position =     0   (OUT)

  trade = target_position - current_position
  # trade ∈ {-2000, -1000, 0, +1000, +2000}
```

This ensures:
- No single indicator controls all signals (rule compliance).
- Requires **2 of 3 indicators** to agree → filters noise.
- Positions constrained to {−1000, 0, +1000}.

### 2.2 Position Tracking State Machine

```
States: OUT (0), LONG (+1000), SHORT (-1000)

Transitions:
  OUT + LONG signal    → BUY 1000   → LONG
  OUT + SHORT signal   → SELL 1000  → SHORT
  LONG + SHORT signal  → SELL 2000  → SHORT
  SHORT + LONG signal  → BUY 2000   → LONG
  LONG + LONG signal   → 0 (already in position)
  SHORT + SHORT signal → 0 (already in position)
```

### 2.3 Trades DataFrame Format

```python
# df_trades: DatetimeIndex × 1 column (symbol name)
# Values: +1000 (BUY), -1000 (SELL), +2000 (reverse short→long),
#         -2000 (reverse long→short), 0 (no trade)

     JPM
2008-01-02    0.0
2008-01-03    0.0
2008-01-07  1000.0   ← BUY (enter long)
...
2008-03-14 -2000.0   ← SELL 2000 (flip from long to short)
```

### 2.4 Chart Requirements

| Chart | Period | Lines |
|-------|--------|-------|
| `manual_is.png` | In-sample 2008–2009 | Purple=Benchmark, Red=Manual, Blue verticals=LONG entries, Black verticals=SHORT entries |
| `manual_oos.png` | Out-of-sample 2010–2011 | Same color scheme |

Both normalized to 1.0 at start: `portval / portval.iloc[0]`.

### 2.5 Performance Table

| Metric | Benchmark IS | Manual IS | Benchmark OOS | Manual OOS |
|--------|-------------|-----------|---------------|------------|
| Cumulative Return | | | | |
| Mean Daily Return | | | | |
| Std Daily Returns | | | | |

---

## 3. Strategy Learner — Design

### 3.1 Framing Trading as Classification

The key insight: **convert a regression problem into a classification problem**.

**Step 1: Compute N-day future return** (label generation)

\[
y_t = \frac{P_{t+N}}{P_t} - 1
\]

We use `N = 5` trading days (1 week lookahead).

**Step 2: Convert to class labels** with impact adjustment

```
LONG  (+1): y_t > +impact      (future return justifies buying after costs)
SHORT (-1): y_t < -impact      (future drop justifies shorting after costs)
CASH  ( 0): |y_t| ≤ impact     (not worth trading)
```

The `impact` threshold creates a **dead zone** — if the expected return doesn't exceed transaction costs, stay flat. This is crucial for Experiment 2.

**Step 3: Build feature matrix** (same indicators as ManualStrategy)

```python
X[t] = [BBP(t), RSI(t), MACD_hist(t)]   # shape: (T, 3)
y[t] = classify(future_return[t])        # shape: (T,)
```

**Step 4: Discretize / standardize features** (required for Random Forest)

```python
# Normalize each feature to [0, 1] using in-sample stats
X_norm = (X - X.mean()) / X.std()
```

or use quantile binning for QLearner.

### 3.2 Random Forest Classifier (Classification-based Learner)

We adapt the existing `BagLearner(RTLearner)` from P3 to **classification mode** by using **mode instead of mean**:

```python
class BagLearnerClassifier:
    def query(self, points):
        predictions = [learner.query(points) for learner in self.learners]
        # Use mode (majority vote) instead of mean
        return scipy.stats.mode(predictions, axis=0).mode[0]
```

Alternatively, we modify RTLearner to return mode at leaf nodes.

**Key hyperparameters:**

| Parameter | Value | Justification |
|-----------|-------|---------------|
| `leaf_size` | 5 | Required ≥ 5 (prevents degenerate overfitting) |
| `bags` | 20 | Variance reduction via bootstrap aggregation |
| `N` (lookahead) | 5 | 1-week forward return |

### 3.3 `add_evidence()` — Training Phase

```
add_evidence(symbol, sd, ed, sv):
  1. Fetch prices for [sd - lookback_buffer, ed]
  2. Compute BBP, RSI, MACD_hist → feature matrix X
  3. Compute N-day future returns → labels y
  4. Discretize/normalize X
  5. Fit BagLearner(RTLearner) on (X_train, y_train)
  6. Store learned model + normalization stats (μ, σ from training set)
```

### 3.4 `testPolicy()` — Testing Phase

```
testPolicy(symbol, sd, ed, sv):
  1. Fetch prices for [sd - lookback_buffer, ed]
  2. Compute BBP, RSI, MACD_hist → feature matrix X
  3. Normalize using STORED in-sample μ, σ (not re-fit!)
  4. Predict classes via BagLearner.query(X)
  5. Convert predicted positions to trades df:
       current_pos = 0
       for t in range(len(predictions)):
           target = predictions[t] * 1000
           trade  = target - current_pos
           current_pos = target
  6. Return df_trades (same as ManualStrategy format)
```

> **Critical:** `testPolicy()` must be deterministic — no re-training, no `query()` (which updates Q-table for QL), only `querysetstate()`. For BagLearner, `query()` is read-only so this is automatic.

---

## 4. Experiment 1 — Manual vs Strategy Learner

### 4.1 Hypothesis

> In-sample, StrategyLearner should outperform ManualStrategy because it can find non-obvious non-linear decision boundaries in the feature space. Out-of-sample, results are less certain — overfitting may hurt the learner.

### 4.2 Chart Requirements

| Chart | Content |
|-------|---------|
| `exp1_is.png` | In-sample: Purple=Benchmark, Red=Manual, Blue=StrategyLearner (normalized) |
| `exp1_oos.png` | Out-of-sample: same color scheme |

### 4.3 Key Discussion Points

- **In-sample**: Learner has access to future labels during training → should outperform manual rules
- **Out-of-sample**: Generalization test — does the learned policy transfer to unseen market conditions?
- **Trade frequency**: StrategyLearner may trade more/less frequently — discuss via number of trades
- **Volatility of returns**: Compare std of daily returns

---

## 5. Experiment 2 — Impact Sensitivity

### 5.1 Hypothesis

> As `impact` increases, the StrategyLearner should trade **less frequently** because the dead zone `|y_t| ≤ impact` grows. Higher impact makes smaller predicted gains unprofitable, so the learner learns to only act on strong signals.

### 5.2 Experimental Setup

```
Commission = $0.00 (always)
Impact values: [0.0, 0.005, 0.01, 0.05, 0.1]
Symbol: JPM, In-sample period only
```

For each impact value, train and test StrategyLearner, then compute:

| Metric | Why it matters |
|--------|---------------|
| **Cumulative Return** | Overall profitability vs. cost sensitivity |
| **Number of trades** | Directly shows trading frequency reduction |

### 5.3 Expected Results Table

| Impact | Cum. Return | Num. Trades |
|--------|-------------|-------------|
| 0.000 | highest | most trades |
| 0.005 | ↓ | ↓ |
| 0.010 | ↓ | ↓ |
| 0.050 | ↓↓ | ↓↓ |
| 0.100 | lowest | fewest trades |

### 5.4 Chart

```
exp2_cumreturn.png  — Line plot: impact (x-axis) vs cumulative return (y-axis)
exp2_numtrades.png  — Line/bar plot: impact (x-axis) vs number of trades (y-axis)
```

---

## 6. Implementation Checklist

### Files to submit to Gradescope

- [ ] `indicators.py` — same as P6, may optimize (vectorize) but not change logic
- [ ] `marketsimcode.py` — from P6
- [ ] `RTLearner.py` — from P3
- [ ] `BagLearner.py` — from P3 (adapted for classification with mode)
- [ ] `ManualStrategy.py` — NEW
- [ ] `StrategyLearner.py` — NEW (template provided, fill in)
- [ ] `experiment1.py` — NEW
- [ ] `experiment2.py` — NEW
- [ ] `testproject.py` — NEW

### Required `author()` in every file

```python
def author():
    return "zabdybaeva3"
```

### Random seed policy

```python
# ONLY in testproject.py, once, using GT ID as seed
np.random.seed(904149968)
```

---

## 7. Technical Gotchas & Common Mistakes

### 7.1 Lookback buffer for indicators

The slowest indicator is MACD (needs 26+9 = 35 days). To get valid indicator values starting at `sd`, load data from `sd - 60 trading days`:

```python
from pandas.tseries.offsets import BDay
prices = get_data([symbol], pd.date_range(sd - BDay(60), ed))
# compute indicators
# then slice: indicators = indicators.loc[sd:]
```

### 7.2 No lookahead bias in testPolicy

```python
# WRONG: normalize using test-period stats
X_norm = (X_test - X_test.mean()) / X_test.std()

# CORRECT: normalize using in-sample (training) stats
X_norm = (X_test - self.train_mean) / self.train_std
```

### 7.3 Positions vs. Trades

```python
# positions array: current holding at each day
positions = np.array([0, 0, 1000, 1000, -1000, 0, ...])

# trades = diff of positions
trades = np.diff(positions, prepend=0)  # [0, 0, 1000, 0, -2000, 1000, ...]
```

### 7.4 Chart must save to file, never show

```python
# WRONG
plt.show()

# CORRECT
plt.savefig("images/manual_is.png", dpi=100)
plt.close()
```

### 7.5 BagLearner classification via mode

RTLearner returns floats. Convert to class labels:

```python
import numpy as np

def classify_predictions(raw_preds):
    result = np.zeros(len(raw_preds), dtype=int)
    result[raw_preds > 0.5]  =  1   # LONG
    result[raw_preds < -0.5] = -1   # SHORT
    return result
```

Or modify BagLearner to use `scipy.stats.mode` instead of `np.mean`.

---

## 8. Performance Benchmarks (Expected)

Based on typical P8 solutions for JPM:

| Strategy | Period | Typical Cumulative Return |
|----------|--------|--------------------------|
| Benchmark | In-sample | ~−18% (JPM dropped in 2008) |
| ManualStrategy | In-sample | > Benchmark (required) |
| StrategyLearner | In-sample | > ManualStrategy (typical) |
| ManualStrategy | Out-of-sample | May be < Benchmark (fine) |
| StrategyLearner | Out-of-sample | Variable |

---

## 9. Report Section Mapping

| Report Section | Code Source | Key Content |
|---------------|-------------|-------------|
| Indicator Overview | `indicators.py` | Describe BBP, RSI, MACD; parameters |
| Manual Strategy | `ManualStrategy.py` | Voting logic, IS/OOS charts, table |
| Strategy Learner | `StrategyLearner.py` | Framing, hyperparams, discretization |
| Experiment 1 | `experiment1.py` | IS+OOS comparison charts + analysis |
| Experiment 2 | `experiment2.py` | Impact table + 2 metric charts |

---

## 10. Dependency Graph (Implementation Order)

```
1. indicators.py      (copy + verify from P6)
        ↓
2. marketsimcode.py   (copy + verify from P6)
        ↓
3. RTLearner.py + BagLearner.py  (copy from P3, add mode support)
        ↓
4. ManualStrategy.py  (uses indicators + marketsimcode)
        ↓
5. StrategyLearner.py (uses indicators + BagLearner + marketsimcode)
        ↓
6. experiment1.py     (uses ManualStrategy + StrategyLearner + marketsimcode)
        ↓
7. experiment2.py     (uses StrategyLearner + marketsimcode)
        ↓
8. testproject.py     (calls all of the above, sets random seed once)
```

Build and test **each layer** before moving to the next. Verify with `grade_strategy_learner.py` at the end.
