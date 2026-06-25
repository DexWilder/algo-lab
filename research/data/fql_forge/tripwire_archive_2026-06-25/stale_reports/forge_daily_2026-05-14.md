# FQL Forge Daily — 2026-05-14

**Run mode:** dry-run
**Total runtime:** 59.9s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 4, 'WATCH': 1, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-BB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 238 | 1.741 | 3769 | -343 | 6.8s | PASS |
| XB-VWAP-EMA-Ladder-MES | MES | Workhorse cross-asset / VWAP closeout test | 881 | 1.097 | 2599 | -3544 | 20.8s | WATCH |
| XB-VWAP-EMA-Ladder-MGC | MGC | Workhorse cross-asset / VWAP closeout test | 373 | 1.252 | 3135 | -1870 | 11.0s | PASS |
| XB-VWAP-EMA-Ladder-MCL | MCL | Workhorse cross-asset / VWAP closeout test | 504 | 1.283 | 3226 | -1407 | 14.6s | PASS |
| XB-VWAP-EMA-Ladder-MYM | MYM | Workhorse cross-asset / VWAP closeout test | 273 | 1.491 | 3186 | -637 | 6.7s | PASS |

## Architecture trends

- PASS assets in this batch: ['MYM', 'MGC', 'MCL', 'MYM']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
