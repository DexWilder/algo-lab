# Phase B Activation Pre-flight — 2026-05-05

**Filed:** 2026-05-05
**Status:** Pre-flight complete. **Recommendation: APPROVE Phase B activation** with 2 small caveats noted below. Operator decides when to load the plist.
**Authority:** T1 diagnostic. No launchd loaded during pre-flight per operator direction.

---

## Verification table (8 checks)

| # | Check | Status | Notes |
|---|---|---|---|
| 1 | `daily_loop.py --dry-run --top N` runs cleanly | ✅ PASS | Smoke-tested with --top 3 (47.8s, 1 PASS / 2 WATCH) and earlier --top 5 (77.3s, 2 PASS / 3 WATCH) |
| 2 | Output paths correct | ✅ PASS | `research/data/fql_forge/reports/` exists; daily MD + JSON + rolling queue file all written |
| 3 | Tripwires active and tested | ✅ PASS (with note) | Simulated unresolved-tripwire condition → loop self-halted, exited non-zero, wrote new `_TRIPWIRE_*.md` (correct halt behavior). **Note:** clearing requires removing ALL `_TRIPWIRE_*.md` files because the halt-write creates a new file (see caveat #1 below). |
| 4 | Plist paths + schedule correct | ✅ FIXED | **BUG FOUND AND FIXED:** original plist had single-dict StartCalendarInterval with Weekday=1 — would have fired Monday only, not weekdays as intended. Fixed by replacing with array-of-dicts pattern (5 entries Mon-Fri × 19:00 local), matching existing FQL plist convention (`scripts/com.fql.daily-research.plist`). plist now passes `plutil -lint`. |
| 5 | Job is report-only — cannot mutate registry or Lane A | ✅ PASS | Code grep: zero writes to `strategy_registry.json`, `data/processed/*`, `logs/trade_log.csv`, `state/*`, controller state, portfolio composition. All file writes scoped to `research/data/fql_forge/reports/` (Forge-only sub-tree). Loop also has no `import` of any registry-mutating module. |
| 6 | Logs written somewhere obvious | ✅ PASS | stdout/stderr logged to `research/logs/forge_daily_loop_stdout.log` / `_stderr.log` — same dir as existing FQL agent logs. Operator can `tail -f` or grep with the rest of the FQL log set. |
| 7 | Activation/deactivation commands documented | ✅ PASS | Inline in plist comment block (lines 5-17). 3-step copy + bootstrap; 2-step bootout + remove. |
| 8 | Cadence is reasonable | ✅ PASS | Weekdays at 19:00 local (= ~6h after NYSE close on Pacific systems; well after operator digest at 17:30 local). Matches existing FQL agent pattern (after-market-close evening job). Each run takes ~30-90s (5 candidates × 10-22s each), well under 5-minute tripwire ceiling. |

---

## Caveats / operator-must-know items

### Caveat 1: Clearing tripwires requires removing ALL `_TRIPWIRE_*.md` files

**Behavior:** when the loop detects an existing tripwire, it ALSO writes a new `_TRIPWIRE_*.md` documenting the halt. So if operator removes only the original tripwire and runs again, the new auto-written one will still be present and trigger another halt.

**Operator clear procedure:**
```bash
# Inspect what's there first
ls research/data/fql_forge/reports/_TRIPWIRE_*

# Diagnose root cause from the file contents
cat research/data/fql_forge/reports/_TRIPWIRE_*.md

# Once root cause is fixed, remove ALL tripwire files
rm research/data/fql_forge/reports/_TRIPWIRE_*.md

# Verify clear
python3 research/fql_forge_daily_loop.py --check-tripwires
```

This is acceptable behavior (defaults to "stay halted" when in doubt) but operator must know the clear procedure. Worth a one-line addition to the design doc; not a blocker.

### Caveat 2: Time convention is local system time, not literal ET

**Behavior:** `Hour=19` means 19:00 LOCAL system time (Pacific on this machine). The phrase "ET" in the design doc and CLAUDE.md is convention-only — actual scheduling uses local time, matching all other FQL plists.

If the operator ever moves systems or changes timezones, the schedule will continue firing at LOCAL 19:00, not at the original ET equivalent. Acceptable for current setup; flagged for future awareness.

---

## Critical safety surface check (Item 5 detail)

The daily_loop's complete file-write scope:

```
research/data/fql_forge/reports/forge_daily_<date>.md         (markdown report)
research/data/fql_forge/reports/forge_daily_<date>.json        (machine-readable)
research/data/fql_forge/reports/forge_queue.md                 (rolling queue)
research/data/fql_forge/reports/_TRIPWIRE_<date>_<reason>.md   (only on halt)
```

Plus stdout/stderr to:
```
research/logs/forge_daily_loop_stdout.log
research/logs/forge_daily_loop_stderr.log
```

**No writes to:**
- `research/data/strategy_registry.json` ✓
- `data/processed/*` ✓
- `logs/trade_log.csv`, `logs/signal_log.csv`, `logs/daily_report.csv` ✓
- `state/account_state.json` ✓
- `inbox/*` (Forge directives, alerts, scoreboard) ✓
- `engine/`, `strategies/`, `scripts/` source code ✓
- Any launchd plist ✓

**No reads of state that influence mutation:**
- Only reads candidate definitions from `research/fql_forge_batch_runner.py` CANDIDATES dict (compile-time constant)
- Only reads price data from `data/processed/*.csv` (read-only)
- No reads of registry status that could conditionally trigger different behavior

The loop is genuinely a closed loop in the math sense: input data → cheap-screen computation → report file output. No path to Lane A.

---

## Recommendation

**APPROVE Phase B activation.** Specifically:

1. **Plist is ready to load.** Bug fixed (weekday array). All paths correct. plutil-validated. Cadence reasonable.
2. **Tripwire safety is real.** Halt-on-anomaly behavior verified. Operator clear procedure documented.
3. **Lane A safety is structurally enforced.** Code surface restricted to Forge-only file writes; no path to registry / portfolio / runtime.

**Activation steps when operator decides to proceed:**
```bash
# 1. Operator review (already happened — this pre-flight)

# 2. Copy to active location
cp "scripts/com.fql.forge-daily-loop.plist.disabled" \
   "$HOME/Library/LaunchAgents/com.fql.forge-daily-loop.plist"

# 3. Load
launchctl bootstrap "gui/$(id -u)" \
   "$HOME/Library/LaunchAgents/com.fql.forge-daily-loop.plist"

# 4. Verify loaded
launchctl list | grep com.fql.forge-daily-loop
```

**Deactivation if needed:**
```bash
launchctl bootout "gui/$(id -u)/com.fql.forge-daily-loop"
rm "$HOME/Library/LaunchAgents/com.fql.forge-daily-loop.plist"
```

**First scheduled fire after activation:** the next weekday at 19:00 local time. The first fire will produce `forge_daily_<date>.md` and update `forge_queue.md` autonomously.

**Operator review cadence after activation:** check the daily report (or `forge_queue.md` rolling) weekly during Friday review. If `_TRIPWIRE_*.md` ever appears, read it and clear before continuing.

---

## What this pre-flight did NOT do

- Did NOT load the launchd plist (operator gate)
- Did NOT mutate the registry
- Did NOT change Lane A surfaces
- Did NOT enable broader Forge automation (Phase C / D remain off-limits)
- Did NOT activate the daily loop for autonomous running (still requires operator launchctl bootstrap)

---

## Files in this pre-flight

- This memo: `docs/fql_forge/phase_b_activation_preflight_2026-05-05.md`
- Plist (bug-fixed): `scripts/com.fql.forge-daily-loop.plist.disabled`
- (No other file mutations beyond the plist fix and this memo)

---

*Filed 2026-05-05. Pre-flight only. No launchd loaded. Operator decides activation.*
