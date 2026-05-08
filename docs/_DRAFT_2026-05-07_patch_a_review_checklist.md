# Patch A Review Checklist (Forge → Source-Helper Feedback Application)

**Filed:** 2026-05-07
**Patch applied:** commit `77e1e5f` (`scripts/fetch_github_leads.py` QUERIES list, +10 / -1)
**Pre-flight:** `docs/_DRAFT_2026-05-07_source_priority_patch_preflight.md`
**Authority:** T1 diagnostic (post-application review). T2 if revert needed.

---

## Why this checklist exists

Patch A was the first end-to-end Forge → source-helper feedback application. It changed what the GitHub source-helper looks for next, with the explicit hypothesis: **transferring the validated `ema_slope + profit_ladder` mechanism into UNDERWEIGHT factors (VALUE/CARRY/VOL/STRUCTURAL) will improve harvest yield in those gaps without amplifying overweight momentum.**

Without measurable success criteria, Patch A is just an input change. With this checklist, it becomes a measurable experiment.

---

## Review dates

| Date | Trigger | What to check |
|---|---|---|
| **Sun 2026-05-10 ~21:00 PT** | After first post-patch source-helper fire | First-fire diagnostic (see §1 below) |
| **Wed 2026-05-13 ~21:00 PT** | After second post-patch source-helper fire | Trend confirmation (see §2 below) |
| **~2026-05-17 (1 week)** | Re-fire `forge_source_feedback.py` | Yield-shift assessment (see §3 below) |

The source-helper plist fires Sun + Wed at 20:00 PT; review the next morning.

---

## §1 — Sunday 2026-05-10 first-fire checklist

After 2026-05-10 20:00 PT source-helper fire, verify the run completed cleanly and inspect the new lead set.

### Run completion checks

- [ ] `research/logs/source_helpers_20260510_*.log` exists (run fired)
- [ ] `~/openclaw-intake/inbox/source_leads/github_leads.md` updated (mtime ≥ 2026-05-10 20:00)
- [ ] `~/openclaw-intake/inbox/source_leads/github_leads_prev.md` archived from prior run
- [ ] No errors in stderr / no truncated output

### Lead-quality inspection

Read the new `github_leads.md`. Count:

- [ ] Total leads returned (cap is `MAX_LEADS = 15`)
- [ ] How many leads explicitly mention any of the new TRANSFER themes:
  - VALUE: "value", "term premium", "earnings yield", "PPP", "fundamental"
  - CARRY: "carry", "regime detection", "trend filter"
  - VOLATILITY: "compression", "Bollinger squeeze", "non-equity"
  - STRUCTURAL: "afternoon session", "close auction", "microstructure"
- [ ] How many leads are **junk** (crypto-only, abandoned repos, irrelevant)
  - Junk rate baseline (pre-Patch A): track against `_manifest.json` history if available
  - Threshold: if junk rate >50% (vs prior baseline of ~30-40%), some new queries are returning low-quality results

### Per-query diagnostic (if any query is returning all junk)

Inspect which of the 10 added queries are returning the junk. The most likely candidates for dropping (smallest hypothesis-evidence backing):

| Query | Hypothesis | If junk → drop because |
|---|---|---|
| "value momentum hybrid systematic" | hybrid academic + practitioner space | Niche term; might return zero or AI-buzzword junk |
| "term premium trading with regime filter" | rates-academic crossover | Term might be too academic; not GitHub-coded |
| "earnings yield futures systematic with momentum filter" | factor-research practitioners | Long query; GitHub-search may underperform |
| "afternoon session microstructure futures" | microstructure research | Niche; may return zero results |

If any query returns zero usable leads twice, drop it. Single-line revert.

### First-fire decision

Choose one based on the inspection above:

- ☐ **CONTINUE** — patch is producing diverse, on-theme leads in target factors
- ☐ **PARTIAL REVERT** — drop specific queries returning all junk; preserve the rest
- ☐ **FULL REVERT** — entire patch is producing worse leads than baseline; revert
- ☐ **WAIT FOR WEDNESDAY** — first fire is one data point; defer decision

---

## §2 — Wednesday 2026-05-13 trend confirmation

After 2026-05-13 20:00 PT source-helper fire, look for cross-fire patterns.

- [ ] Compare 2026-05-10 leads vs 2026-05-13 leads (`github_leads_prev.md` from Wed run is Sun's set)
- [ ] How many UNIQUE new leads (not duplicates of Sun)
- [ ] How many of the new TRANSFER queries returned at least 1 viable lead across both fires
- [ ] Did any specific query return zero usable leads BOTH fires? → drop candidate
- [ ] Did momentum-themed leads decrease (without the removed `"momentum trading systematic python"` query)?
- [ ] Triage outcomes: how many Sun leads have been classified by the next harvest cycle? (ACCEPT / ACCEPT-COMPONENT / REJECT)

### Triage signal — the actual yield test

The query change is upstream; triage outcomes are what matters. By Wed, we should have at least Sun's leads triaged.

- [ ] Count Sun leads that became ACCEPT (any priority) in `harvest_triage/` notes
- [ ] Count Sun leads that became ACCEPT-COMPONENT
- [ ] Count Sun leads that became REJECT (note reason: junk, redundant, off-theme, etc.)
- [ ] Of accepted Sun leads, how many fall into VALUE/CARRY/VOL/STRUCTURAL families?

### Wednesday decision

- ☐ **CONTINUE** — yield is shifting toward underweight factors as predicted
- ☐ **PARTIAL ADJUST** — drop specific underperforming queries; keep the rest
- ☐ **REVERT** — patch is not improving factor yield; revert and try different theme set
- ☐ **EXPAND** — patch is working; consider Patch B (Reddit) or other factors

---

## §3 — ~Saturday 2026-05-17 yield-shift assessment

After ~1 week, re-run the feedback layer and compare:

```
python3 research/forge_source_feedback.py --lookback-days 14 --save
```

- [ ] New `forge_source_feedback.py` report exists at `docs/reports/forge_source_feedback/2026-05-17_forge_source_feedback.md`
- [ ] Section 4's harvest priority recommendations: still TRANSFER, or shifted?
- [ ] Compare Forge run history: any new candidates from Patch-A-influenced harvest making it to PASS verdicts?
- [ ] Compare registry: any new entries in VALUE/CARRY/VOL/STRUCTURAL families since 2026-05-07?

### Success criteria

The patch is **successful** if at least one of these is true after 1 week:

- [ ] At least 1 ACCEPT-priority lead (any underweight factor) was harvested as a direct result of Patch A's new queries
- [ ] Junk rate did not increase (stayed ≤ 40%)
- [ ] No reverts needed (all 10 new queries returning usable leads at least occasionally)
- [ ] Triage backlog showed shift toward VALUE/CARRY/VOL/STRUCTURAL representation

The patch is **a partial success** if 2-3 queries underperform but the bulk continue producing useful leads.

The patch is **a failure** if junk rate spiked, no underweight factor leads materialized, or triage rejection rate increased.

### One-week decision

- ☐ **PROMOTE TO PERMANENT** — Patch A becomes the new baseline; consider Patch B (Reddit)
- ☐ **TRIM AND KEEP** — drop underperforming subset; keep working subset; document
- ☐ **REVERT FULLY** — write retrospective explaining what didn't work; queue different theme set

---

## §4 — Revert procedure (if needed)

If full revert is needed:

```bash
# Revert just the QUERIES change (one targeted commit)
git -C "/Users/chasefisher/projects/Algo Trading/algo-lab" revert 77e1e5f
git -C "/Users/chasefisher/projects/Algo Trading/algo-lab" push origin main
```

If partial revert (drop specific query):

```bash
# Edit scripts/fetch_github_leads.py and remove the target query
# Single-commit, single-line removal
git -C "/Users/chasefisher/projects/Algo Trading/algo-lab" add scripts/fetch_github_leads.py
git -C "/Users/chasefisher/projects/Algo Trading/algo-lab" commit -m "Lane B / Forge: drop underperforming Patch A query <name> per review checklist"
git -C "/Users/chasefisher/projects/Algo Trading/algo-lab" push origin main
```

No additional safety steps needed — `fetch_github_leads.py` is read by source-helpers at fire time; next fire picks up the new query list.

---

## §5 — What we'll learn regardless of outcome

Even if Patch A fully fails, we learn:

- Whether the heuristic theme mapping (asset → keywords) produces actionable harvest queries
- Whether GitHub-search is the right channel for niche TRANSFER themes (vs Reddit, YouTube, academic)
- What junk-rate baseline looks like under richer query diversity
- Whether 10-query patches are the right granularity for Forge feedback (vs smaller increments)

Each of these informs the next iteration regardless of pass/fail outcome.

---

## §6 — Filing this review

After the 2026-05-17 assessment, file the outcome at:

`docs/reports/source_priority_patches/2026-05-XX_patch_a_outcome.md`

Include:
- Final decision (PROMOTE / TRIM / REVERT)
- Per-query yield data
- Junk-rate change
- Underweight factor representation change
- Lessons for next patch

---

*Filed 2026-05-07. Lane B / Forge. T1 review framework. No mutations occur via this checklist; it's a measurement plan. Operator can update success criteria / thresholds at any time.*
