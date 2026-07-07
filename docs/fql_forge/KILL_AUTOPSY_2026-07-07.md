# KILL AUTOPSY — what did the failures have in common? (2026-07-07)

Meta-analysis of 30 tested mechanisms, coded by three axes (observability, frequency, framing), cross-tabulated against outcome. Survive-rate weights: SURVIVED (watch/ingredient/screen_pass) = 1.0, WEAK = 0.5, DEAD = 0.

## The three cuts

| OBSERVABILITY | dead | weak | survived | survive-rate |
|---|---|---|---|---|
| DIRECT (measures the behavior) | 5 | 3 | 3 | **41%** (n=11) |
| PRICE (pure price/vol transform) | 4 | 5 | 0 | 28% (n=9) |
| PROXY (rough stand-in) | 9 | 0 | 1 | **10%** (n=10) |

| FRAMING | dead | weak | survived | survive-rate |
|---|---|---|---|---|
| **regime-conditioning** | 0 | 4 | 3 | **71%** (n=7) |
| carry / relative-value | 4 | 2 | 1 | 29% (n=7) |
| **outright-directional** | 14 | 2 | 0 | **6%** (n=16) |

| FREQUENCY | survive-rate |
|---|---|
| event 36% · weekly 25% · daily 27% · **intraday 12%** | |

The 4 partial-survivors: M08 dealer-gamma (proxy, **conditioning**), M09 term-structure carry (direct), M07 month-end (direct, conditioning), M75 funding-stress (direct, conditioning). **3 of 4 are conditioning; 3 of 4 are direct.**

## What this says
1. **Failure is STRUCTURED, not uniform.** Outright-directional prediction is near-dead (6%); regime-conditioning survives at 71%. Proxies (10%) die far more than direct measurements (41%). If durable edges simply didn't exist, we'd expect *uniform* failure — we don't see that. The structure itself is the finding.
2. **We have been building the wrong KIND of signal.** 16 of 30 tested mechanisms were outright-directional — the worst-surviving class. The lab's instinct ("predict the next move") is the losing frame. **Conditioning the distribution of an existing book is where signal concentrates.**
3. **Intraday is a graveyard** at our resolution/cost (12%). The overnight-anomaly result reinforces this: real *gross* edge, killed by per-trade cost.

## The claim I retract
Last turn I wrote *"the bottleneck is edge-existence."* **Unearned.** This autopsy cannot distinguish two hypotheses:
- **H-edge:** durable structural edges are genuinely rare.
- **H-observability:** we've only ever tested PROXIES and COARSE direct measurements. **Zero high-resolution direct institutional measurements have been tested** — never real option-by-option dealer gamma from an IV surface, never live inventory, never ETF create/redeem. Killing a max-OI *proxy* for dealer gamma (M19) says almost nothing about dealer gamma.

The data is equally consistent with both. I over-concluded.

## The discriminating experiment (how to actually tell them apart)
Take a mechanism killed **via proxy** and re-test it with a **high-resolution direct** measurement, framed as a **conditioner**:
- **Dealer gamma:** M19 (max-OI proxy) → KILLED. Direct version = invert ES option settlements (stat_type=3, held) to a real IV surface → signed dealer GEX → test as an intraday *conditioner* of MES realized vol/mean-reversion (not an outright pin trade).
- If the DIRECT+conditioning version **also** clean-kills → evidence for H-edge (the edge isn't hiding in resolution).
- If it **survives where the proxy failed** → H-observability confirmed → the acquisition priority becomes high-resolution direct measurements, full stop.

This reframes acquisition ranking: **value a dataset by whether it converts a proxy-kill into a direct test**, not by "another mechanism."

## Search reshaped (operationalized, not just noted)
Every mechanism now carries `observability`/`frequency`/`mtype`/`survivor_fit` in the library. Queue re-ranked by `survivor_fit` (conditioning + direct + event/weekly). New top: M66 FOMC-drift, M74 HY-credit regime, M76 post-event vol-crush, M68 VRP, M77 skew — all direct conditioners. Outright + intraday + proxy mechanisms deprioritized.
