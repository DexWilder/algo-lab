# Rescue / false-kill review (2026-06-29) — were any kills UNFAIR?

> P1 item. For every major KILL/shelve, check the 5 false-kill causes: (a) bad harness, (b) bad data, (c) broken/
> blunt cost, (d) proxy-correlation, (e) sample error — plus (f) ORB/lookahead-dependency. Classify CLEAN_KILL
> (robust) vs RETEST_REQUIRED (kill may be an artifact of a fixable flaw). Report-only.

## Key insight on contamination direction
The ema_slope lookahead INFLATES results → it can only create false *validations*, never false *kills*. So nothing
killed under the contaminated engine is a false-kill candidate on that account (clean metrics are ≤ contaminated).
The cost-model reassessment (2026-06-29) already showed the marginal shelves are ROBUST to realistic cost → cost
is not a false-kill source here either.

## Ledger
| Branch | Kill reason | bad harness? | bad data? | blunt cost? | proxy? | sample? | Verdict |
|---|---|---|---|---|---|---|---|
| XSMOM cross-asset | MCL roll artifact drove it; clean-proxy (USL/DBO) collapsed it | no | **was the cause, REMOVED** | no | retested clean | ok | **CLEAN_KILL** (artifact removed → no edge) |
| Crude relative-strength | 100% MCL roll artifact | no | yes→tested | no | no | ok | **CLEAN_KILL** |
| nfp_level_breakout | lookahead(mild) + neg median + 47% concentration | checked | no | costed | no | n=83 ok | **CLEAN_KILL** (fails on edge-quality even ignoring leak) |
| vol_managed_equity | long-beta, no alpha vs buy&hold | **date-aligned harness used** (caught daily reindex) | no | costed | no | ok | **CLEAN_KILL** (beta, not alpha) |
| P03 auction concession | per-event Sh ~0, DSR 0.41, incoherent both-sides | event-correct | TreasuryDirect ok | costed | no | n=64 ok | **CLEAN_KILL** |
| COT naive reversal | one-sided; well-sampled long-fade NEGATIVE; best-of-48 | both-sides done | CFTC real | costed | beta-confounded noted | flagged small-n | **CLEAN_KILL** (non-naive COT could be pre-registered later — that's new, not a rescue) |
| P14 VWAP-reversion | extension continues; all sides neg | causal | volume-native | costed | no | huge n | **CLEAN_KILL** |
| P15 volume-momentum | high-RVOL no better than low; DSR 0 | causal | volume-native | costed | no | huge n | **CLEAN_KILL** |
| basket B1/B2 | B1 fail; B2 passes only optimistic-slip + 1-leg/1-yr | no-optimizer | ok | **stress-tested x1/2/3** | decorrelated checked | ok | **CLEAN_FAIL** (robust to cost stress) |
| ORB family, stop_run, zn_afternoon, fx_daily | INVALIDATED by lookahead | — | — | — | — | — | not a kill — falsely VALIDATED, correctly invalidated |

## Shelved / RETEST (not clean kills — genuinely open)
| Branch | Status | Why retest |
|---|---|---|
| treasury_rolldown_carry | **RETEST_REQUIRED_BESPOKE** | never given a correct multi-asset point-in-time carry harness; NOT killed |
| TSMOM / vol-carry / ZN month-end / overnight | CLEAN_BUT_WEAK / SCREEN_PASS_RETAINED | real-but-sub-threshold; cost-robust; basket-leg only |
| close-only daily mechanisms | low-priority volume-retest eligible | could add volume-confirmation, but P14/P15 volume kills lower the prior |

## Conclusion
**No false-kills found.** The kills are robust to harness (date-alignment fixed where needed), data (artifacts
removed/retested), cost (participation-model reassessment = no verdict change), and sample. The contamination
direction (inflation) means lookahead never caused a false kill. The only genuinely OPEN (not-killed) item is
treasury_rolldown (needs a bespoke harness — queued), plus the standing option to pre-register a NON-naive COT
hypothesis (new work, not a rescue). The discipline held: we killed real things for real reasons.
