# Novelty Packets — generated 2026-07-02
> generative engine (templates x instruments, dedup, feasibility-scored). Space=108 combos, covered=38/108, emitted-this-run=8, queued-LOCAL=6.

| score | dim | mechanism | instr | horizon | data | availability | harness |
|---|---|---|---|---|---|---|---|
| 9.6 | carry | carry vs own rolling term-structure baseline (not raw sign) | CL | daily | PERCONTRACT | LOCAL | term-structure-carry |
| 9.6 | carry | carry vs own rolling term-structure baseline (not raw sign) | GC | daily | PERCONTRACT | LOCAL | term-structure-carry |
| 9.6 | roll/settlement | longs must roll front->deferred over the roll window | MES | roll window | PERCONTRACT | REPULL | term-structure |
| 9.6 | roll/settlement | longs must roll front->deferred over the roll window | MNQ | roll window | PERCONTRACT | REPULL | term-structure |
| 9.0 | month-end/rebalance | duration/equity index funds rebalance in the last session(s) | M2K | last 1-3 sess | CALENDAR | LOCAL | calendar-adapter |
| 9.0 | month-end/rebalance | duration/equity index funds rebalance in the last session(s) | MES | last 1-3 sess | CALENDAR | LOCAL | calendar-adapter |
| 9.0 | microstructure | overnight order imbalance resolves in the opening auction | 6B | first 30m | M1 | LOCAL | intraday-path |
| 9.0 | microstructure | overnight order imbalance resolves in the opening auction | 6E | first 30m | M1 | LOCAL | intraday-path |