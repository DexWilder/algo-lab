# What separates this lab from effective systematic research orgs — and what we can close in a year (2026-07-08)

Base camp is built (validation, DSR, causality audit, archives, mechanism library, lifecycle, self-audit, closure metrics, paper packets). **That's enough base camp. Now climb.** This is an honest gap analysis: not "hire 400 PhDs," only gaps a solo+AI operation can realistically close in ~12 months. Grounded in our own evidence, not marketing.

**Caveat (important):** elite firms differ enormously — a market-maker (Jane Street) and a medium-horizon quant (Two Sigma) and a black-box shop (RenTech) have almost nothing in common operationally, and most of their process is not public. I am not projecting one model. I'm naming capabilities that are *generically* associated with durable systematic edge and that we visibly lack.

## Not closeable (name them, stop pretending otherwise)
Raw capital scale · sub-millisecond/colocated execution (kills the entire intraday-HFT lane — consistent with our autopsy: intraday survives 12%) · large quant/engineering headcount · seven-figure alt-data budgets · prime-broker order-flow data. We do not compete on these. Any strategy whose edge *requires* them is out of scope by construction.

## The 10 closeable gaps, ranked by (leverage × how-closeable)

**1. Portfolio construction & sleeve SUPPLY — the biggest gap, and I started closing it today.**
Elite systematic PnL comes from *combining* many orthogonal modest signals with a real risk model — not one workhorse. We spent months hunting standalone workhorses. Built the combination layer today; it immediately proved the binding constraint is **sleeve supply**: we hold ~1.5 trustworthy orthogonal streams (TSMOM clean-but-0.72; spreadMR_GC high-but-DSR-borderline). A book needs 5–6. *Action:* make "graduate trustworthy orthogonal sleeves" the explicit target (not "find a workhorse"); use Sharpe/Kelly-aware weighting (naive risk-parity lowered Sharpe); down-weight fragile sleeves.

**2. Experiment-design rigor (CV).** We do per-sweep DSR but NOT purged/embargoed K-fold or combinatorial-purged CV (López de Prado), and no program-wide trial accounting. Our OOS is a single H1/H2 split — weak. *Action:* implement purged+embargoed CV and a program-level multiple-testing ledger. Pure code, no approval/data.

**3. Idea sourcing beyond arbitraged literature.** FOMC pre-announcement drift and the overnight anomaly both *decayed to death* in our data — textbook post-publication arbitrage. Sourcing from famous papers means sourcing already-crowded trades. *Action:* shift to (a) original mechanism generation from data structure, (b) capacity-constrained/structural edges big players ignore, (c) combinations of our own banked ingredients.

**4. Targeted observability (data), not shotgun.** Our autopsy could not distinguish "edge absent" from "edge unobserved" because we've only tested proxies + coarse-direct measurements. *Action:* buy the ONE dataset that converts a proxy-kill into a direct test — full ES option-settlement history (the observability discriminator). Operator-gated (cost + key).

**5. Execution & CAPACITY realism.** Cost/impact is load-bearing: the overnight anomaly was gross-alive/net-dead; spreadMR_GC is high-Sharpe but tiny-capacity (calendar spread). We model cost crudely and ignore capacity entirely. *Action:* make capacity a first-class gate — a real-but-untradeable-at-size edge is a KILL for our purposes.

**6. Signal-decay awareness.** Published edges decay; we evaluate as if stationary. *Action:* recency-weighted metrics + explicit decay tracking (would have flagged FOMC-drift faster).

**7. Higher-quality automated hypothesis generation.** batch_screen = naive single-market price transforms (we proved that space dead). *Action:* feature-based / combinatorial generation of *genuinely different* hypotheses with built-in multiple-testing correction — raise the quality, not the count, of shots.

**8. Live/paper feedback loop.** Zero live feedback today; everything is in-sample-era backtest. *Action:* get TSMOM to paper — the first real OOS + fill-quality feedback. Operator-gated (Y/N).

**9. Horizon / return-target coverage.** We over-indexed on daily *directional* futures PnL. Our survivors are conditioning / carry / relative-value. *Action:* deliberately cover vol / dispersion / carry / cross-sectional books, where our own evidence says edge concentrates.

**10. A conditioning-overlay framework.** We've banked 3 macro-stress conditioners (funding, credit, GEX) with nowhere to apply them. *Action:* build the overlay framework so conditioners tilt a *validated* book's risk — valuable the moment gap #1 produces a book.

## Roadmap (sequence)
- **Now, no approval needed (I drive these):** #1 sleeve-supply + combination (started), #2 CV rigor, #3 better sourcing, #5 capacity gate, #6 decay-aware metrics, #10 overlay framework. These are the climb.
- **Operator decisions (unlock disproportionate value):** #4 option-settlement pull (settles the observability question), #8 TSMOM→paper (starts the live loop).
- **The reframe:** the goal is no longer "find the elite workhorse." It is "manufacture a *supply* of trustworthy orthogonal sleeves and a construction layer that turns them into a book." That is the actual business of systematic research, and it's the mountain — base camp is done.

## The one-line internalization
The research universe is always larger than today's queue. When a queue's EV drops, the move is to generate a better queue or climb a bigger gap — never to declare the world empty or wait for approval. Research is never gated; only capital is.
