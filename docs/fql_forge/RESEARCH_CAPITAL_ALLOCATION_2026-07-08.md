# Research capital-allocation decision — Q reallocation to information acquisition (2026-07-08)

**This is an investment decision, not a coding decision.** Six months of evidence justifies changing the resource mix for one quarter: validation is strong, false-positive detection is strong, and the marginal return of the current *style* of held-data mining is measurably falling (3 domains → 1 thin sleeve; one prior "win" was an artifact). The binding constraint is no longer our ability to reject ideas — it's **the quality of ideas entering the system.** So for the next quarter, buy better inputs.

## Reallocation (tactical, one quarter — not permanent)
| Bucket | Old target | **Q target** |
|---|---|---|
| Information acquisition | 40% | **60%** |
| Mechanism generation | 25% | 15% |
| Validation | 20% | 15% |
| Portfolio integration | 10% | 5% |
| Infrastructure | 5% | 5% |

## The buy-list — ranked by mechanism-value unlocked per dollar (computed from our own library)
Value = EV-weight × survivor-fit of the mechanisms each dataset makes *directly observable* (vs the proxies that keep dying).

| Tier | Dataset | Unlock value | Cost | Every item answers: what becomes observable |
|---|---|---|---|---|
| **0 — free, do now** | EIA inventory + index-reconstitution calendar | 10.5 | **$0** (free API key / deterministic dates) | energy-inventory surprise, natgas seasonal, Russell rebalance |
| **1 — trivial, auto-approve** | VX futures term structure | 11.2 | **~$8** | vol-carry (VRP, term-structure roll), vol-of-vol, IV-momentum — a *different, less-arbitraged premium class* |
| **2 — the primary investment** | **ES option settlement history (2019–26)** | **17.5** (4 of 7 are conditioning-type) | **medium — get the quote first** | dealer gamma (DIRECT, not the max-OI proxy that died), skew, dispersion, vol-crush, VRP — *and it resolves the observability fork* |
| 3 — defer | single-name options / ETF flows / execution depth | ≤3.5 each | high | dispersion, create/redeem, microstructure — revisit only if Tier 2 produces a survivor |

## The decision (forcing it out of limbo — invest or consciously decline, no indefinite hold)
1. **Tier 0 + 1 — recommend: approve now.** Free + ~$8, within standing auto-approve. Highest value-per-dollar on the board. Needs your Databento key + EIA free registration; exact commands already in `DATA_UNLOCK_SPRINT`. I'll wire the ingestion the moment data lands.
2. **Tier 2 — recommend: get the price tag, then decide.** Before committing, run Databento's **free** cost estimate so the investment has a real number:
   ```python
   import os, databento as db
   c = db.Historical(os.environ["DATABENTO_API_KEY"])
   print(c.metadata.get_cost(dataset="GLBX.MDP3", symbols=["ES.OPT"], stype_in="parent",
       schema="statistics", start="2019-01-01", end="2026-06-30"))
   ```
   Then the decision is concrete: *"$X buys the single largest block of unobserved mechanism-value we hold and settles whether the edge is unobserved or absent."* If $X is (say) under a few hundred dollars, it dominates another month of held-data mining. If it's large, we consciously decline and reallocate — but we **decide**, we don't leave it frozen.

## Why this is the right business call, stated plainly
- The highest-EV branch (data acquisition) has been at **0% of actual effort** because it's the only branch that needs you. That's not a footnote — it's the single most important number on the board, and leaving it frozen is the least informative outcome.
- Even a **null** from the option-settlement class is high-value: it's the falsification test that tells us the edge isn't merely unobserved, which would redirect the whole program (horizon / return-target / venue) rather than have us mine held data for another quarter.
- Everything below Tier 2 I drive without you (audits, generation, CV rigor, portfolio analytics) — this reallocation does not stall the drivable streams; it unfreezes the one that's stuck.

**Default if no decision in ~2 weeks:** I execute Tier 0 (free) and treat Tier 1–2 as consciously deferred, re-ranked at the next biweekly review — so it never sits in silent limbo.
