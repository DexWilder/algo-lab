# XB-ORB-EMA-Ladder: Strategy Genealogy

*The only strategy to survive the full FQL validation gauntlet.*

## The Winning Recipe

```
Entry:   orb_breakout    (from ORB-009 family)
Filter:  ema_slope       (from momentum_pullback_trend family)
Exit:    profit_ladder   (original — designed for crossbreeding engine)
Params:  stop_mult=2.0   (upgraded from 0.5 after stop sweep)
```

Result: PF 1.59-1.67 across 5 assets (MNQ, MES, MGC, M2K, MCL),
with 898-1183 trades per asset, positive median trade, and 8/8 years
profitable on MNQ.

---

## Component Origins

### 1. ORB Breakout Entry
- **Source:** ORB-009 family (`strategies/orb_009/`, `orb_enhanced/`)
- **Mechanism:** Price breaks 30-min opening range high/low after 09:30 ET
- **Key design:** 6 bars = 30 min on 5m data, one trade per direction per day
- **What survived:** The breakout trigger logic, unchanged
- **What was dropped:** Original ORB-009 exit logic (ATR trail)

### 2. EMA Slope Filter
- **Source:** momentum_pullback_trend family + standard trend-following
- **Mechanism:** EMA21 > EMA50 = uptrend (allow longs), vice versa (shorts)
- **Key design:** Uses mid-term (21) vs slow (50), not fast (8)
- **What survived:** The trend-direction gate, unchanged
- **What was dropped:** Pullback entry logic from the parent family
- **Why it works:** ~59% directional accuracy → raises trade WR from ~50% to 57%

### 3. Profit Ladder Exit (THE CRITICAL COMPONENT)
- **Source:** Original — designed specifically for the crossbreeding engine
- **Mechanism:** Ratcheting stops at R-milestones:
  - At 1R → lock 0.25R
  - At 2R → lock 1R
  - At 3R → lock 2R
- **Key design:** Lets winners run while locking in gains at each milestone
- **Why it's critical:** This is the ONLY exit that produces positive median
  trade. Every other exit tested (ATR trail, chandelier, time stop, midline
  target) produces negative median — meaning most trades lose money and
  the edge is tail-dependent.
- **Note:** target_mult and trail_mult params are currently ignored (fixed ratchet)

---

## What Was Tried and Dropped

### Entry alternatives (14 tested, all failed)
| Entry | Result | Why it failed |
|-------|--------|---------------|
| donchian_breakout | 0 trades | Interface issue (since fixed, but still untested) |
| pb_pullback | 4/4 profitable | Negative median on MES — tail-dependent |
| vwap_continuation | 4/4 profitable | Negative median on 3/4 assets |
| bb_reversion | 4/4 profitable | Negative median on MES |

**Verdict:** ORB is the only entry that produces positive median on all 4 assets.

### Filter alternatives (5 tested, all failed)
| Filter | Result | Why it failed |
|--------|--------|---------------|
| vwap_slope | 3/4 profitable | Negative median on MGC and M2K |
| bandwidth_squeeze | 3/4 | Negative median |
| session_morning | 3/4 | Negative median |
| session_afternoon | 2/4 | Below profitability threshold |
| none (unfiltered) | 3/4 | Negative median |

**Verdict:** EMA slope is the only filter that maintains positive median cross-asset.

### Exit alternatives (5 tested, all failed)
| Exit | Result | Why it failed |
|------|--------|---------------|
| atr_trail | 4/4 profitable | **ALL negative median** across all assets |
| chandelier | 4/4 profitable | **ALL negative median** |
| time_stop | 4/4 profitable | **ALL negative median** |
| midline_bb | 1/4 profitable | Most assets lose money |
| midline_vwap | 1/4 profitable | Most assets lose money |

**Verdict:** Profit ladder is the ONLY exit that maintains positive median.
This is the most important finding from the genealogy.

---

## Why the Hybrid Was Better Than Raw Parents

### Raw parent (ORB-009): PF 1.14 on MGC (SALVAGE)
- Default ATR-based exit let winners run too long
- Stopped out too early on pullbacks
- No trend filter → took counter-trend breakouts that reversed
- Result: thin edge, tail-dependent, failed concentration gates

### Hybrid (XB-ORB-EMA-Ladder): PF 1.59-1.67 across 5 assets
Three changes made the difference:

1. **EMA slope filter** removed ~40% of counter-trend entries → WR 50% → 57%
2. **Profit ladder exit** locked gains at milestones instead of trailing →
   positive median trade (winners captured, losers limited)
3. **Wider stop** (2.0 ATR vs 0.5) gave more room → fewer stops hit

**The critical insight:** The profit ladder is what makes the median positive.
The EMA filter raises win rate. Together: 57% WR × positive median = distributed
edge, not lottery ticket. This is the structural signature that passed all
concentration gates and deep validation.

---

## Template for Future Elite Strategy Creation

Based on the genealogy, a new elite strategy should:

1. **Start with an entry that fires frequently** (~14+ trades/month)
2. **Add a trend/regime filter** that removes counter-signal noise (~40% reduction)
3. **Use an exit that produces positive median trade** — this is non-negotiable.
   The profit ladder ratchet is currently the only known exit that does this.
4. **Test on multiple assets** — cross-asset generalization is the concentration
   check that kills lottery tickets
5. **Sweep stop distance** — wider stops often improve PF by reducing premature exits
6. **Verify positive autocorrelation** — the asset must have enough intraday momentum
   for breakout follow-through (autocorr > -0.05)
