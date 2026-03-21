# Post-Expansion Evaluation Checklist — April 3/4, 2026

*First meaningful checkpoint after widening harvest lanes + helper automation.*
*Run: `python3 scripts/harvest_quality_review.py --days 14 --save`*
*Then review this checklist manually.*

---

## 1. Did source leads convert into harvest notes?

**Data source:** `_manifest.json` lifecycle entries + harvest_quality_review

| Metric | Pass | Fail | Where to check |
|--------|------|------|----------------|
| GitHub leads → notes | ≥ 2 notes sourced from GitHub URLs | 0 notes from GitHub | harvest_quality_review "Notes by Source" |
| Reddit leads → notes | ≥ 1 note sourced from Reddit URLs | 0 notes from Reddit | Same |
| YouTube leads → notes | ≥ 1 note sourced from YouTube | 0 notes from YouTube | Same |
| Blog leads → notes | ≥ 2 notes from blog RSS sources | 0 notes from blogs | Same |
| Digest leads → notes | ≥ 1 note from Quantpedia | 0 notes from digests | Same |
| Overall conversion | ≥ 10% of leads produced notes | < 5% conversion | manifest lifecycle picked_up vs fetched |

**If FAIL:** Claw is not reading `source_leads/`. Check task instructions
and verify `inbox/source_leads/` files are present on Monday mornings.

---

## 2. Are notes capturing component_type tags?

**Data source:** alerts engine + manual sample

| Metric | Pass | Fail |
|--------|------|------|
| ≥ 30% of new notes have component_type field | Tag adoption is working | Still defaulting |
| ≥ 3 non-full_strategy types seen (entry_logic, filter, etc.) | Fragment capture is real | Only full_strategy |
| At least 1 filter, 1 exit_logic, or 1 sizing_overlay note | Components are being captured | Zero fragments |

**If FAIL:** Tighten Claw task instructions. Add explicit examples of
fragment notes to `_note_template.md`. Consider adding "generate at
least 1 component note per harvest batch" as a directive rule.

---

## 3. Is source convergence appearing?

**Data source:** manual review of new notes vs registry

| Metric | Pass | Fail |
|--------|------|------|
| ≥ 2 ideas where the same mechanism appeared from different source types | Convergence is real | No cross-source matches |
| At least 1 registry entry updated with convergent_sources | Tracking is working | convergent_sources still empty on all entries |

**If FAIL (and expected):** Convergence takes time. If zero after 2
cycles, this is normal — the catalog may not be deep enough yet. Do
NOT build convergence scoring module. Wait for 2 more cycles.

**If PASS:** Consider building Phase 2 convergence scoring. The data
exists to make it useful.

---

## 4. Are widened lanes filling portfolio gaps?

**Data source:** harvest_quality_review "Portfolio Gap Fit" section

| Gap | Pass (notes targeting it) | Fail |
|-----|--------------------------|------|
| VOLATILITY | ≥ 3 new VOL notes from non-equity sources | 0 new VOL notes, or all on MES/MNQ |
| VALUE | ≥ 2 new VALUE notes (was 0 ideas pre-expansion) | Still 0 VALUE notes |
| Energy | ≥ 1 MCL/CL strategy note | Still 0 energy notes |
| Short-bias | ≥ 2 short-biased or both-direction notes | All notes are long-only |
| Non-morning session | ≥ 3 notes targeting afternoon/close/daily | All notes are morning equity |

**If FAIL on VALUE/Energy:** These were blind spots. Strengthen search
terms in harvest_config.yaml. Add explicit VALUE and Energy examples
to Claw task instructions.

---

## 5. Which lanes are high-signal vs noisy?

**Data source:** harvest_quality_review "Noise Rate by Source"

| Outcome | Threshold | Action |
|---------|-----------|--------|
| Lane noise rate > 40% | Too noisy | Lower cap or tighten filters |
| Lane produces 0 notes despite leads | Not converting | Check if Claw is reading the leads |
| Lane produces notes with highest acceptance rate | High signal | Consider raising cap |
| One lane > 50% of all notes | Dominant | Ensure diversity by adjusting other lane caps |

**Expected result:** Blog and digest lanes should be highest signal.
Reddit should be noisiest. GitHub variable.

---

## 6. Are caps/prompts/filters ready for tuning?

**Decisions to make at this checkpoint:**

| Decision | Criterion |
|----------|-----------|
| Raise a lane cap | Lane consistently hits cap AND acceptance rate > 60% |
| Lower a lane cap | Lane noise rate > 40% OR produces mostly duplicates |
| Tighten Claw prompts | Notes lack component_type OR miss obvious gaps |
| Add search terms | A portfolio gap has 0 targeting notes |
| Add RSS feeds to blog helper | Blog lane is high-signal AND more feeds are available |
| Disable a lane | Lane produces 0 useful notes after 2 cycles (very unlikely) |

---

## 7. Is Phase 2 convergence scoring justified?

**Decision gate:**

| Condition | Decision |
|-----------|----------|
| ≥ 5 cross-source matches exist in harvest notes | **BUILD** convergence scoring |
| 2-4 cross-source matches | **STAGE** — design but don't build yet |
| 0-1 cross-source matches | **WAIT** — catalog not deep enough |

**What "cross-source match" means:** The same testable mechanism
described in notes from 2+ different source_category values. Example:
a carry trade concept appearing in both a Quantpedia digest and a
TradingView script, independently.

---

## Parallel: Forward Evidence Check

*Not harvest-related, but this checkpoint also covers probation.*

| Strategy | Check | Expected by Apr 3 |
|----------|-------|-------------------|
| VolManaged-EquityIndex | Daily weight data accumulating? | ~10 forward days |
| ZN-Afternoon-Reversion | Any forward trades? | 2-4 trades |
| Treasury-Rolldown | First rebalance signal? | ~March 31 signal |
| TV-NFP-High-Low-Levels | April 4 is NFP day — any trade? | 0-1 trades |
| NoiseBoundary-MNQ-Long | Still generating? PF direction? | 5-10 trades |

---

## Checkpoint Outputs

After running the evaluation:

1. **Update harvest_config.yaml** with any cap/filter changes
2. **Update Claw task instructions** if component tagging needs tightening
3. **Record convergent sources** in registry if any found
4. **Decide on Phase 2** — build convergence scoring or wait
5. **Update this checklist** with results for the next checkpoint (April 17)
