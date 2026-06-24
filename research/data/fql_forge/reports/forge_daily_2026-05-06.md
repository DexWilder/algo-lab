# FQL Forge Daily — 2026-05-06

**Run mode:** dry-run
**Total runtime:** 63.0s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 4, 'WATCH': 1, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-BB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 289 | 1.522 | 4146 | -637 | 11.0s | PASS |
| XB-BB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 460 | 1.223 | 2397 | -874 | 14.2s | PASS |
| XB-BB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 235 | 1.756 | 3796 | -343 | 6.6s | PASS |
| XB-VWAP-EMA-Ladder-MES | MES | Workhorse cross-asset / VWAP closeout test | 881 | 1.097 | 2599 | -3544 | 20.2s | WATCH |
| XB-VWAP-EMA-Ladder-MGC | MGC | Workhorse cross-asset / VWAP closeout test | 370 | 1.263 | 3211 | -1870 | 10.9s | PASS |

## Architecture trends

- PASS assets in this batch: ['MGC', 'MCL', 'MYM', 'MGC']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
