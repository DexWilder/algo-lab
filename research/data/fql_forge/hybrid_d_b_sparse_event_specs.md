# Hybrid D-B — Sparse / Tail / Event Spec Generation

> **Status:** Spec catalog. Some EXECUTABLE this cycle (08f); others DATA_REQUIRED.
> **Recorded:** 2026-06-08 per operator decision #94 Hybrid D-B.
> **Authority:** Lane B research; report-only.

## Sprint context

After cycles 08c+08d wiped out 32 non-ORB workhorse candidates, Hybrid D pivots to:
- D-A: build `range_compression_break` primitive (DONE, running cycle 08e)
- D-B: restart sparse/tail/event hunt on calendars that are clean (this doc)

## Executable specs (data available, running this cycle)

### Spec 1 — NFP-MCL event-window expansion (cycle 08f, RUNNING)

Extend the proven NFP-MGC-Long-2h Packet #1 template to MCL (crude oil).

Hypothesis: NFP releases (1st Friday, 8:30 ET) create USD flows that affect crude pricing.

| Label | Asset | Direction | Exit bars |
|---|---|---|---:|
| NFP-MCL-Long-2h | MCL | long | 24 |
| NFP-MCL-Short-2h | MCL | short | 24 |
| NFP-MCL-Long-1h | MCL | long | 12 |
| NFP-MCL-Long-4h | MCL | long | 48 |
| NFP-MCL-Long-EOD | MCL | long | 72 |

Stress: lightweight 3-rung (1× / 2×+1tick / 2×+2ticks) on any WATCH. Family review vs NFP-MGC Packet #1 required if any PAPER_PACKET emerges.

## DATA_REQUIRED specs (queued, NOT executable until data unblocked)

### Spec 2 — Treasury auction calendar candidate

Operator: "exact Treasury auction calendar only if trivial."

**Status: DATA_REQUIRED.** Treasury auction calendar is publicly available from TreasuryDirect.gov but not in the repo. Building an ingestion is **not trivial** (calendar varies by tenor: 2Y/3Y/5Y/7Y/10Y/20Y/30Y schedules differ; reopening auctions add noise; surprise tap auctions during stress windows).

**Decision:** Do NOT build. Defer until operator explicitly approves Treasury calendar ingestion as a separate primitive build.

### Spec 3 — WASDE / USDA report candidate

Operator: "WASDE / USDA if calendar and asset mapping are clean."

**Status: DATA_REQUIRED.** WASDE (World Agricultural Supply and Demand Estimates) publishes monthly around the 12th, primarily affecting grain markets (CBOT corn / soybeans / wheat). Asset mapping to our universe is **not clean**:
- We do not currently have grain micros (ZC corn, ZS soybeans, ZW wheat) in data tree.
- WASDE could marginally affect MCL (crude) via ethanol/biofuel pathway, but evidence is thin.

**Decision:** Do NOT build. Defer until either (a) grain assets added to data tree, or (b) operator approves WASDE-on-MCL diagnostic as a focused spec.

### Spec 4 — COT-shift carry/regime candidate

Operator: "COT-shift or carry/regime candidates only if data available without rabbit hole."

**Status: DATA_REQUIRED.** Commitments of Traders (CFTC) report publishes Friday for prior Tuesday positioning. Useful for regime detection but requires:
- CFTC COT data ingestion (CSV from cftc.gov; manageable but not in repo)
- Asset mapping (CFTC product codes ↔ our symbols)
- Signal-construction (smoothed position-extremes, position-shift z-scores)

The "rabbit hole" warning applies: COT-shift signals require careful primitive design (multiple sub-features) before producing edge candidates.

**Decision:** Do NOT build. Defer until COT primitive is operator-approved as a focused multi-step build.

### Spec 5 — EIA crude inventory release candidate

Wednesday 10:30 ET (when no holiday). Strong intraday signal on MCL historically.

**Status: DATA_REQUIRED.** EIA Weekly Petroleum Status Report calendar is regular but requires:
- Calendar ingestion (cycle-shifts due to holidays)
- Optional: inventory print + expectations for surprise-signal

**Decision:** Defer. The calendar is approximately Wednesday 10:30 (with holiday shifts to Thursday). Could spec as a coarse event-window candidate without surprise data — simpler than Treasury auctions but still requires calendar-ingestion work.

### Spec 6 — OPEC conference outcome candidate

Operator: "commodity-specific events with clean calendars."

**Status: DATA_REQUIRED.** OPEC + OPEC+ meeting dates are irregular and the outcome (production cut/increase/hold) is the signal, not the timing. Requires hand-curated outcome list. Not "clean calendar."

**Decision:** Do NOT build.

## Summary

| Spec | Asset class | Data status | Action this cycle |
|---|---|---|---|
| NFP-MCL expansion | Crude (MCL) | CLEAN (calendar verified) | **EXECUTABLE** — running 08f |
| Treasury auction | Rates | DATA_REQUIRED | Defer |
| WASDE / USDA | Grains | DATA_REQUIRED (asset gap) | Defer |
| COT-shift | Multi | DATA_REQUIRED (rabbit hole risk) | Defer |
| EIA crude | Crude (MCL) | DATA_REQUIRED (cal. ingestion) | Defer |
| OPEC conference | Crude (MCL) | DATA_REQUIRED (curated list) | Defer |

**This cycle Hybrid D-B leg = NFP-MCL expansion only.** Other specs queued for operator decision on data-ingestion priority.

## Operator-decision asks queued

| Ask | Question | Effort |
|---|---|---|
| EIA-MCL coarse spec | Approve coarse EIA-Wed-MCL event-window candidate using calendar-only (no surprise data) | Low (calendar build only) |
| Treasury auction primitive | Approve building Treasury auction calendar ingestion as a focused primitive | Medium (multi-tenor + reopen logic) |
| Grain asset onboarding | Approve adding ZC/ZS/ZW to data tree to enable WASDE candidates | High (data pipeline + cost config) |
| COT-shift primitive | Approve full COT signal-construction primitive build | High (multi-feature; rabbit-hole risk) |

## Source artifacts

- `research/forge_cycle_2026-06-08f_nfp_mcl.py` (NFP-MCL expansion, RUNNING)
- `research/event_window_engine.py` (existing harness)
- `research/forge_nfp_calendar_verify.py` (verified NFP calendar, reused)
- `docs/fql_forge/paper_packet_drafts/EVT-NFP-MGC-Long-2h_2026-06-04.md` (Packet #1 template)
