# Dual Thrust threshold primitive — pre-build spec (2026-06-01)

Spec document for a new entry primitive to be added to `research/crossbreeding/crossbreeding_engine.py`. **No implementation in this document.** Awaiting operator authorization before build.

This spec is the deliverable of Path B planning per the Forge continuous-execution model. Dual Thrust is the highest-leverage primitive build from Phase 4b backlog translation: unlocks 3 SCREENABLE backlog notes (N1, N6, N10).

---

## What Dual Thrust is

Practitioner / TradingView-popular daily breakout system, sourced from Chinese commodity-trading literature, formalized by Michael Chalek. The mechanism:

1. Compute a "range" from the previous N days' OHLC
2. Set today's upper threshold = today's open + K1 × range
3. Set today's lower threshold = today's open − K2 × range
4. Enter long on a session break above upper, short on a session break below lower
5. Reversal allowed: if price traverses from one threshold to the other, flip direction
6. Flatten at end of session (no overnight hold by default)

It is **not** the same as ORB — ORB uses the *current* session's opening range; Dual Thrust uses *historical* OHLC plus the current session's open.

---

## Canonical formula

For each session t:
```
HH(t) = max( high(t-1), ..., high(t-N) )       # highest high of last N days
LC(t) = min( close(t-1), ..., close(t-N) )     # lowest close of last N days
HC(t) = max( close(t-1), ..., close(t-N) )     # highest close of last N days
LL(t) = min( low(t-1),   ..., low(t-N) )       # lowest low of last N days

range(t) = max( HH(t) - LC(t),  HC(t) - LL(t) )

upper(t) = open(t) + K1 * range(t)
lower(t) = open(t) - K2 * range(t)
```

Defaults from literature: `N=5`, `K1=0.5`, `K2=0.5` (symmetric). Common alternatives: K1=0.7/K2=0.7 (less sensitive), K1=0.3/K2=0.3 (more sensitive).

Asymmetric K1 ≠ K2 produces a directional bias — useful when paired with a slower trend filter.

---

## Required parameters (exposed in candidate spec)

```python
{
    "dt_lookback": 5,            # N: days in historical range calc
    "dt_k1": 0.5,                # upper threshold multiplier
    "dt_k2": 0.5,                # lower threshold multiplier
    "stop_mult": 2.0,            # reuse standard primitive stop framework
    "target_mult": 4.0,
    "trail_mult": 2.5,
}
```

`dt_lookback`, `dt_k1`, `dt_k2` are Dual-Thrust-specific. The remaining params are shared with other entries (stop/target/trail).

---

## Asset / session assumptions

**Asset universe (from backlog notes N1, N6, N10):**
- N1: ZN/ZB (rates), CL/MCL (energy), GC/MGC (gold)
- N6: CL/MCL (energy, afternoon variant)
- N10: CL/MCL, GC/MGC, ZN/UB

All non-equity. The primitive must work on assets where the engine doesn't have specific opening-range logic (rates, energy, gold are NOT US equity-index morning-session-specific).

**Session assumptions:**
- Default formulation uses *daily-bar* OHLC for the historical range, but operates *intraday* (enter on intraday break of the daily-bar-derived threshold).
- For 5-minute data: the previous N days' OHLC must be computed by resampling 5m bars to daily, OR by tagging each 5m bar with the day's OHLC computed up to session start.
- "Open(t)" = price at the first bar of the relevant session. For non-equity overnight sessions (CL/MCL/MGC), pick the most operationally clean session start (suggest: regular session start, e.g. 09:00 ET for CL).

**Session-specific variants:**
- Standard daily Dual Thrust (N1, N10): one signal per session, computed from prior-day OHLC
- Afternoon-specific (N6): morning-session OHLC (09:00-12:30 ET) replaces "prior day's OHLC", afternoon trigger window (14:00-15:30 ET)

For the **first build**, implement the standard daily variant only. Afternoon variant (N6) is a parameter override that can be layered later.

---

## Stop / exit compatibility

Dual Thrust primitive returns `(signal, stop, target)` per the existing entry-primitive contract, so it composes with every existing exit primitive (`profit_ladder`, `chandelier`, `time_stop`, `atr_trail`, `midline_target`). No new exit code needed.

Default stop framework reuses existing pattern:
- Long: stop = close − ATR × `stop_mult`
- Short: stop = close + ATR × `stop_mult`
- Target: close ± ATR × `target_mult`

Optionally: "Dual Thrust native exit" — flatten at end of session — can be added later as a new exit primitive `eod_flatten` if backlog notes specifically require it. Not in this build.

---

## Data fields required

Required new features in `compute_features`:
- `dt_upper_{N}[i]` — upper threshold for the session containing bar `i`
- `dt_lower_{N}[i]` — lower threshold for the session containing bar `i`

Computation:
1. Resample 5-minute bars to daily OHLC (use existing `datetime` column, group by date).
2. For each daily bar, compute HH/LC/HC/LL over the prior N daily bars (shift(1).rolling(N)).
3. Compute range(t) = max(HH−LC, HC−LL).
4. For each daily bar t, compute upper(t) = open(t) + K1 × range(t), lower(t) = open(t) − K2 × range(t).
5. Forward-fill these daily values onto every 5m bar within day t.

Pseudocode (Python-style):
```python
daily = df.set_index("datetime").resample("D").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
daily["HH_N"] = daily["high"].shift(1).rolling(N).max()
daily["LC_N"] = daily["close"].shift(1).rolling(N).min()
daily["HC_N"] = daily["close"].shift(1).rolling(N).max()
daily["LL_N"] = daily["low"].shift(1).rolling(N).min()
daily["range"] = np.maximum(daily["HH_N"] - daily["LC_N"], daily["HC_N"] - daily["LL_N"])
daily["dt_upper"] = daily["open"] + K1 * daily["range"]
daily["dt_lower"] = daily["open"] - K2 * daily["range"]

# Map back to 5m grid by date
df["date"] = pd.to_datetime(df["datetime"]).dt.date
date_to_thresholds = daily[["dt_upper", "dt_lower"]].to_dict("index")
df["dt_upper_5"] = df["date"].map(lambda d: date_to_thresholds.get(d, {}).get("dt_upper", np.nan))
df["dt_lower_5"] = df["date"].map(lambda d: date_to_thresholds.get(d, {}).get("dt_lower", np.nan))
```

Primitive signal logic:
```python
def entry_dual_thrust(f, i, state, params):
    """Dual Thrust threshold breakout: break above upper / below lower, reversal allowed."""
    N = params.get("dt_lookback", 5)
    key_u = f"dt_upper_{N}"
    key_l = f"dt_lower_{N}"
    if key_u not in f:
        key_u, key_l = "dt_upper_5", "dt_lower_5"
    upper = f[key_u][i]; lower = f[key_l][i]
    if np.isnan(upper) or np.isnan(lower):
        return 0, 0, 0
    if f["close"][i] > upper and not state["long_traded_today"]:
        stop = f["close"][i] - f["atr"][i] * params.get("stop_mult", 2.0)
        target = f["close"][i] + f["atr"][i] * params.get("target_mult", 4.0)
        return 1, stop, target
    if f["close"][i] < lower and not state["short_traded_today"]:
        stop = f["close"][i] + f["atr"][i] * params.get("stop_mult", 2.0)
        target = f["close"][i] - f["atr"][i] * params.get("target_mult", 4.0)
        return -1, stop, target
    return 0, 0, 0
```

---

## Expected cost sensitivity

Dual Thrust is a daily-cadence breakout — typically produces **1 trade per day max** per direction (via the `long_traded_today` / `short_traded_today` guards). With the workhorse-frequency anchor of ~1-2 trades/day on indices, we expect:

- ~250 trades/year per asset (daily cadence × ~250 sessions)
- Per-trade hold typically minutes to hours (intraday exit at EOD or stop/target)
- Average move per trade: should exceed 1 ATR (held until stop/target hits)

**Cost-ratio prediction:** lower than Phase 5's high-frequency-MCL failures because trade count is much smaller. With MCL friction ~$5/trade and expected per-trade gross of ~$50-100 (ATR-scaled), cost ratio should land 5-15%. This should not be a cost-ratio kill.

**Hidden risk:** the reversal allowance ("reverse if price traverses from one threshold to the other") doubles the trade count per session in choppy conditions. Backlog note N1 specifically permits this. For the first build, include the daily-flag guards so only one long + one short per day max; revisit if PASS-eligible candidates need reversal logic.

---

## Backlog notes unlocked (3)

1. **N1 — 2026-05-14_01** Dual Thrust ORB for rates and commodities. Direct fit. Assets ZN, ZB, CL, MCL, GC, MGC. Same-day flatten.
2. **N6 — 2026-04-16_03** Dual-Thrust Afternoon Energy Release. **Variant** — uses morning OHLC instead of prior-day OHLC. Will require an `intraday_session` mode parameter in v2; not in this build.
3. **N10 — 2026-05-07_02** Dual Thrust + Donchian + ATR risk frame. Combines Dual Thrust trigger with Donchian filter. After this build + the existing fixed Donchian primitive, this composite is testable.

---

## Validation plan (after build, before reporting back to operator)

Small, focused — not a broad sprint. Tests the primitive on the 2-3 most direct backlog candidates:

1. **XB-DualThrust-EMA-Ladder-MCL** — N1 spec on energy. Tests cost-ratio prediction.
2. **XB-DualThrust-EMA-Ladder-MGC** — N1 spec on gold. Cross-asset check.
3. **XB-DualThrust-EMA-Ladder-ZN** — N1 spec on rates. Tests whether Dual Thrust transfers to rates (where ORB failed cost-ratio in Phase 3).
4. **XB-DualThrust-Donchian-ATRTrail-MCL** — N10 composite. Tests interaction with fixed Donchian primitive.

If 1+ produce PASS_TO_FORWARD_CLOCK: that's a wire candidate for operator review.
If all MUTATE/DEFER/KILL: the primitive is correctly expressed but the strategy itself doesn't have edge on these assets. Either way, the primitive itself is now in the engine and usable for future sprints.

---

## What's NOT in this build (deferred to v2 if needed)

- Reversal logic (cross-threshold flip mid-session) — requires state machine change
- Afternoon-specific variant (N6) — requires session-window parameter
- End-of-session flatten exit (`eod_flatten`) — would be a new exit primitive
- Asymmetric K1 ≠ K2 directional-bias mode — supported via params but not tested
- Anything beyond daily-cadence (intraday Dual Thrust on 15m/30m bars)

---

## Estimated implementation scope

- `compute_features` additions: ~25 lines (daily resample + threshold calc + 5m-grid forward-fill)
- `entry_dual_thrust` primitive: ~20 lines
- `ENTRY_MAP` registration: 1 line
- Default `BASE_PARAMS` additions: 3 keys
- Validation script (4 candidates): ~30 lines

**Total: ~80 lines of code.** Approximately 30–45 minutes implementation + 5–10 minutes validation. Significantly cheaper than a candidate sprint.

---

## Awaiting operator decision

Per the user's spec:
> "Then wait for approval before build, unless we separately authorize the primitive build."

Standing by for:
- (a) Authorize build of standard daily Dual Thrust (this spec, this scope)
- (b) Modify scope (e.g., include afternoon variant N6)
- (c) Defer build (operator wants different next-task direction)

---

## Stale-evidence log: Donchian family sweep

For audit hygiene per the user's instruction:

The 2026-04 family sweep results in `research/data/xb_orb_family_sweep_results.json` for the `entry_donchian` and `entry_donchian_breakout` rows were produced **before** the 2026-05-28 fix to `entry_donchian_breakout` (commit 2825c09). Those REJECT verdicts were based on a buggy primitive that produced 0 trades. **Do not cite the pre-fix Donchian family-sweep results as evidence in future decisions.** Future Donchian comparisons must reference post-2825c09 measurements only.

---

## Pointers

- Engine bug fix: commit `2825c09` (research/crossbreeding/crossbreeding_engine.py)
- Phase 4b backlog translation routing the 3 unlocked notes: `docs/reports/forge_sprint/2026-05-28_phase4b_backlog_translation_v2.md`
- Path A results (Donchian-MGC exit variants): `docs/reports/2026-06-01_path_a_donchian_mgc_exit_variants.json`
- Primitive-bottleneck doctrine: `feedback_primitive_coverage_bottleneck.md` (memory)
