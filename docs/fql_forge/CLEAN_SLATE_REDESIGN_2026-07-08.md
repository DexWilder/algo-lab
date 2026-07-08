# "If I were starting Algo Lab today, with everything we've learned, what would I build differently?"
2026-07-08 · zero backtests · a first-principles review, forced deliberately.

## The reframe that reorganizes everything: two different capabilities
- **Capability 1 — hard to fool.** GOOD ENOUGH that it should no longer *dominate* engineering time — NOT "solved forever." No validation system is ever finished (there's always another artifact, another audit — spreadMR's execution-lag test was one we only added last week). The claim is about *resource allocation*: six months ago more validation infrastructure was the highest-value work; today it probably isn't. DSR, causality audit, artifact detectors, execution-lag/autocorr audits, block-bootstrap, closures, memory — this caught its own broken bootstrap, killed a Sharpe-2.9 mirage, refused the FOMC/overnight decays. Keep extending it opportunistically; stop letting it be the default sink for effort.
- **Capability 2 — good at finding opportunity.** UNPROVEN. One thin real sleeve (TSMOM). The next chapter's entire job is to test, *efficiently*, whether capability 2 can be built — not to keep polishing capability 1.

Those are different capabilities. Conflating them is why the lab felt stuck: we kept scoring capability 1 (rigor) and calling the low output a failure, when the honest statement is "rigor is good enough to stop dominating effort; opportunity-finding is unproven."

## The old implicit thesis — now doubted by our own evidence
*"Many independent, accessible, directional edges exist in micro-futures on daily/intraday bars; find them one at a time via mechanism testing."* Evidence against it: outright-directional mechanisms survive 6% (vs conditioning 71%); intraday is a 12% graveyard; 3 mined domains → 1 thin sleeve; the one prior "win" was an artifact; famous anomalies (FOMC drift, overnight) had already decayed. The thesis is probably too optimistic. That is a *finding*, not a failure.

## What I'd KEEP (~80%) — do not tear down
- The entire anti-fooling stack. It's the crown jewel and the reason you can trust any future "yes."
- Memory / lifecycle / closures / audit discipline; report-only + capital-gate.
- TSMOM (thin but real, CI [0.17,1.29]); the mechanism library **as a map of where edge is NOT** — that map has real value.

## What I'd BUILD DIFFERENTLY (~20%) — the actual pivot
1. **Data-first, not mechanism-first.** Invert the funnel: start from "what can we observe that others don't bother to?" and derive mechanisms from that — observability is the scarce input, not ideas. (Capital-allocation shift already started: 60% information acquisition this quarter.)
2. **Construction / overlay / execution / sizing are FIRST-CLASS research products, not afterthoughts.** With ~1 sleeve, the leverage is in *using* few weak-but-real components well — dynamic sizing, risk overlays, regime conditioning (survives 71%), capital allocation. Your question — "why assume the next win is another signal?" — is right: the next win may be a *better use of what we have*.
3. **Source from advantage, not arbitraged literature.** Published anomalies are crowded by definition (FOMC/overnight proved it). Source from: our own observability edge, structural/capacity-constrained edges big players ignore, and combinations of banked components.
4. **Execution & capacity are a gate from day 1.** Every candidate priced for impact/capacity *before* it's called a sleeve. spreadMR would have died on day 1, not week 2.
5. **Deprioritize intraday-directional UNTIL new evidence changes its EV** (not permanently). Current evidence shows diminishing returns in our *current* intraday search (12% survival) and it's where our retail data/cost tier is weakest — so stop hunting there *now*. But that's a stance conditioned on present evidence, not a proof the domain is empty: new data, a different horizon, or a different formulation can reopen it. Revisit when the expected value changes, not on a whim and not never.
6. **Pre-committed checkpoints** (below) replace open-ended hope with bounded decisions — the structural fix for "wasting years."

## The pre-committed checkpoints — decisions, not vibes
Each has a *branch written in advance*, so a miss triggers a strategy re-eval, not "work harder."
- **90 days (2026-10-06): Did we unlock materially new observability?** i.e. acquired + tested the option/vol-structure data class. **Miss → the acquisition decision has been left frozen too long; force invest-or-abandon on that branch.**
- **180 days (2027-01-04): ≥1 additional portfolio-improving component graduated, OR the highest-value branches (observability class) decisively retired?** **Miss → the "accessible-edges" thesis is failing; begin an explicit universe/horizon/return-target change (not more mining).**
- **365 days (2027-07-08): Has the process repeatedly generated candidates that survive rigorous validation (≥3 independent survivors)?** **Miss → the current data/markets/research-model is the wrong vehicle; change course. Sunk cost is not a reason to continue.**

## The honest bottom line
The lab's product today is not a strategy. It is (a) a machine that is hard to fool, and (b) a validated map of where the edge is *not*, in this universe. That is real, and it is worth more than a lucky backtest — but it is capability 1. The next chapter is a focused, checkpointed test of capability 2, run primarily through **observability + construction**, not more directional mechanism mining. I am not attached to this architecture. If the checkpoints say capability 2 can't be built with the current data, markets, or model, the right move is to change the vehicle — and I'll say so plainly when the evidence does, not push because we've already invested. That's the promise, made mutual.
