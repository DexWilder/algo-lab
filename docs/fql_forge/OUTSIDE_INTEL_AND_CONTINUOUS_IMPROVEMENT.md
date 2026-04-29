# Outside Intel and Continuous Improvement

**Filed:** 2026-04-29 as canonical reference for the input lane that feeds the operating system.

**Companion to:** `hot_lane_architecture.md` and `post_may1_build_sequence.md` (the operating system itself). This doc is the **input lane** — without it, the operating system converges to local optima and stops learning.

**Authority:** T0 advisory. Items in this doc are watched / trialed / adopted / retired by operator decision; nothing in this lane is auto-applied to runtime.

**Premise.** Elite trading systems do not get there by execution alone. They get there by learning continuously from outside the system: papers, code, tools, methodologies, operating-principles from elite shops, AI/agent advances, and targeted reading. Without a governed outside-intel lane, the hot lane converges; with one, it stays adaptive. This doc is the lane.

---

## 1. The five lanes this doc feeds

Every external input is classified by which operating lane it might improve. Inputs that don't map to a lane are noise.

| Lane | What it improves | Examples of relevant input |
|---|---|---|
| **Discovery** | Idea generation, harvesting | Academic papers, blogs, code repos, podcasts |
| **Recombination** | Hot-lane generator + donor catalog | Component composition research, ML feature engineering |
| **Validation** | First-pass + battery + portfolio scoring | Robustness methodology, deflated SR, walk-forward design |
| **Execution** | Forward runner, broker integration, data | Microstructure research, broker tooling, data feeds |
| **Governance** | Operating principles, elite-shop practices | Books and writeups on Renaissance / AHL / DE Shaw / Two Sigma operating model |

**Plus AI/Tooling monitor (cross-cutting):** new models, agents, IDE tools, MCP servers, notebook tools, dashboard tools.

---

## 2. Source watchlist — current

Each row: source, lane(s) fed, why it matters, status, last reviewed.

### 2.1 Discovery sources

| Source | Lane | Why it matters | Status | Last reviewed |
|---|---|---|---|---|
| Reddit r/algotrading, r/quant | Discovery | Already feeding harvest engine; high noise, occasional novel mechanism | Active (Claw harvest) | 2026-04-29 |
| TradingView (script library) | Discovery | Source of community-tested ideas; useful for filter/exit components | Active (Claw harvest) | 2026-04-29 |
| GitHub (quant/futures repos) | Discovery + Recombination | Implementation sketches; donor candidates from validated repos | Active (source helpers) | 2026-04-29 |
| SSRN / arxiv (Q-fin) | Discovery + Validation | Academic factor research, methodology papers | Active (academic harvest) | 2026-04-29 |
| Quantpedia | Discovery | Curated factor strategies; cross-reference for novelty check | Watching | 2026-04-29 |
| Robot Wealth blog + courses | Discovery + Validation | High-quality systematic-trading methodology; futures-relevant | Watching | 2026-04-29 |
| Concretum / Hudson and Thames | Recombination + Validation | ML for finance, factor combinations, Lopez de Prado-adjacent material | Watching | 2026-04-29 |
| Substack quant authors (curated list TBD) | Discovery | Newsletter format compresses signal | Watching | 2026-04-29 |

### 2.2 Validation / methodology sources

| Source | Lane | Why it matters | Status | Last reviewed |
|---|---|---|---|---|
| Lopez de Prado papers (SSRN) | Validation | Deflated Sharpe, probabilistic backtesting, false-discovery control | Watching | 2026-04-29 |
| Bailey & Lopez de Prado backtest literature | Validation | Anti-overfitting methodology; directly relevant to factory thresholds | Watching | 2026-04-29 |
| Bootstrap / walk-forward methodology research | Validation | Sharper validation battery design | Watching | 2026-04-29 |

### 2.3 Execution sources

| Source | Lane | Why it matters | Status | Last reviewed |
|---|---|---|---|---|
| Databento (data feeds) | Execution | Current feed provider; monitor for new instruments / asset classes | Active | 2026-04-29 |
| Exchange microstructure research | Execution | Slippage/impact modeling, order routing optimization | Watching | 2026-04-29 |
| Broker API improvements (current broker) | Execution | New order types, fill quality, margin efficiency | Watching | 2026-04-29 |

### 2.4 Governance / operating-principles sources

| Source | Lane | Why it matters | Status | Last reviewed |
|---|---|---|---|---|
| Rob Carver (Systematic Trading book + blog) | Governance + Discovery | Explicitly elite-shop systematic methodology; closest-in-spirit author | Reading queue | 2026-04-29 |
| Patrick Boyle YouTube | Governance | Operating principles + history of systematic shops | Watching | 2026-04-29 |
| Top Traders Unplugged podcast | Governance | Interviews with systematic CTAs; operating-model intel | Watching | 2026-04-29 |
| Many Happy Returns / Quant insider podcasts | Governance | Operating-model and risk-management intel | Watching | 2026-04-29 |
| Andreas Clenow books (Following the Trend, etc.) | Governance + Validation | Trend-systematic methodology, futures-specific | Reading queue | 2026-04-29 |

### 2.5 AI / Tooling monitor (cross-cutting)

| Source / Tool | Lane | Why it matters | Status | Last reviewed |
|---|---|---|---|---|
| Anthropic Claude model releases | Cross-cutting | This system runs on Claude; new model = new generation/analysis capability | Active | 2026-04-29 |
| Anthropic Skills / Agent SDK | Cross-cutting | Better orchestration of multi-step agent tasks | Watching | 2026-04-29 |
| MCP servers (especially for trading data / research) | Discovery + Execution | Standardized agent access to tools; could power future automation | Watching | 2026-04-29 |
| Cursor / IDE agents | Operator efficiency | Faster code iteration on the operating layer | Watching | 2026-04-29 |
| ChatGPT Tasks | Operator efficiency | Already adopted (weekly Friday update) | Adopted 2026-04-29 | 2026-04-29 |
| Marimo / next-gen notebooks | Operator efficiency | Reactive notebooks for backtest exploration | Watching | 2026-04-29 |
| Local LLM deployments (for batch backtest analysis) | Validation | Cost-bounded inference for large-scale post-hoc analysis | Watching | 2026-04-29 |

---

## 3. Books / deep-reads queue

### 3.1 High-priority targeted reads (relevant to current edge gaps)

| Book | Author | Lane it improves | Why now |
|---|---|---|---|
| Systematic Trading | Rob Carver | Governance + Validation | Closest-in-spirit elite-shop methodology; directly applicable to FQL operating model |
| Smarter Investing in Any Economy | Rob Carver | Governance | Portfolio-level systematic principles |
| Advances in Financial Machine Learning | Marcos Lopez de Prado | Validation + Recombination | Sharper validation methodology; component combination research |
| Machine Learning for Asset Managers | Marcos Lopez de Prado | Recombination | Component-economy theory closest to what hot lane needs |
| Following the Trend | Andreas Clenow | Discovery + Validation | Trend-systematic methodology, futures-specific, real-world track record |
| Trading Evolved | Andreas Clenow | Validation + Execution | Practical Python systematic implementation; backtest framework comparison |
| Inside the Black Box | Rishi Narang | Governance | Elite-quant shop overview; operating-model intel |

### 3.2 Explicit NOISE list (do not add to high-priority)

| Category | Reason for exclusion |
|---|---|
| General "how to trade" books | Not systematic; discretionary framing |
| Crypto-focused books | Out of FQL instrument universe |
| Single-stock equity strategy books | FQL universe is futures (micros) |
| Technical-analysis manuals not grounded in stats | No edge, high noise |
| Books on retail psychology / mindset | Not the bottleneck |
| Most "trading legends" biographies | Story over method; rarely actionable |

### 3.3 Reading review cadence

- **Per book:** must produce ≥1 concrete operating-system change OR be marked "read, no application" within 30 days of completion. "Read, no application" books help calibrate noise list.
- **Queue length:** ≤5 books in queue at any time. New addition forces a deferral or removal.
- **Reading rate:** ~1 book / month sustained, slower in operationally-heavy weeks.

---

## 4. Source intake criteria (what gets added to watchlist)

A source is added only if it can answer all three:

1. **Which lane does it feed?** If unclear, do not add.
2. **What edge would it produce?** Must be specific (e.g., "novel filter component," "validation methodology," "operator-efficiency tool"). "Generally interesting" = noise.
3. **What's the trial cost?** Define the time/dollar cost of a 30-day trial before adding.

A source that can't answer all three is curiosity, not intel.

---

## 5. Source retirement criteria (what gets removed)

Sources have a half-life. The watchlist is not a graveyard.

- **Watching status > 90 days without a single concrete contribution:** retire OR move to archive (not active watch)
- **Adopted tool not used in >60 days:** review and either commit or retire
- **Book in queue >180 days unread:** remove from queue (added back only if priority resurfaces)
- **Source produces noise > signal for 3 consecutive monthly reviews:** retire

Retirement is not failure — it's the watchlist staying small enough to be useful. A 50-source watchlist is theater; a 15-source watchlist gets read.

---

## 6. Intel → action rule

Reading without operating-system change is theater.

**Every quarter, each active item on this watchlist must produce ≥1 of:**

- A specific change to the hot lane / generator / kill lane / scoring / governance
- A new tool trial that completes within 60 days
- An explicit "no, this doesn't apply" with reasoning (also valuable — calibrates noise)

Items with zero outputs across two consecutive quarters → retired.

**The intel-to-action ratio is the success metric for this lane.** A watchlist with 20 sources and 0 changes/quarter is failing. A watchlist with 8 sources and 4 changes/quarter is elite.

---

## 7. Cost ceiling (operator time)

The outside-intel lane has a budget. Without one, it eats time from the operating system.

| Activity | Hard ceiling |
|---|---|
| Weekly source review (Friday update) | ≤30 minutes |
| Monthly source/tool/book triage | ≤90 minutes |
| Quarterly retirement + intake review | ≤2 hours |
| Active reading time | ≤4 hours/week |

If ceilings exceeded for 2 consecutive weeks → triage. Outside-intel cannot become a backlog masquerading as continuous improvement.

---

## 8. Reporting cadence

| Cadence | Owner | Output |
|---|---|---|
| **Weekly Friday update (automated via ChatGPT task)** | Operator | Executive: live system, survivors-per-week, what changed, biggest risk, next-week focus, 1-2 outside-learning ideas |
| **Twice-monthly full assessment** | Claude (evidence packet) + Operator (pressure-test) | Deep truth audit; merged into one canonical assessment |
| **Quarterly intel review** | Operator | This doc reviewed; sources retired/added; books triaged; tools committed/retired |
| **Phase / checkpoint events** | Joint | Phase 0 Review (May 8), May 1 checkpoint, etc.; intel reviewed against phase exit criteria |

---

## 9. Anti-patterns

What this lane **does not** do:

1. **No reading-list theater.** Books read without operating change are noise unless they explicitly calibrate the noise list.
2. **No source proliferation without retirement.** Every quarterly review must close at least as many sources as it opens, until the watchlist stabilizes ≤25 active items.
3. **No "elite shops do X" without testing X applies here.** Operating-principles intel from large shops must be evaluated against single-operator FQL constraints; what works at AHL with 100 staff may not transfer.
4. **No tool envy.** "Try every new AI tool" fails; trials are committed (60-day window) or skipped.
5. **No outside-intel becoming its own backlog.** §7 cost ceiling + §6 intel-to-action rule jointly prevent this.
6. **No "watching forever" status.** Watching > 90 days with zero output → retire.

---

## 10. Initial action items (post-May-1, before Phase 0 Review)

- ☐ Confirm this doc lives in the Friday weekly update review loop
- ☐ Identify 1-2 books from §3.1 to start reading first (highest expected impact: Carver's Systematic Trading and Lopez de Prado's MLAM)
- ☐ Decide on 1-2 AI/tooling trials to commit to in May (candidates: Anthropic Skills/Agent SDK, MCP for trading data, local LLM for batch analysis)
- ☐ Populate full Substack / podcast watchlist (currently TBD in §2.1)
- ☐ Review the first quarterly intel report at the end of July 2026

---

## What this doc is NOT

- **Not a reading list.** It is a governed input lane with intake/retirement criteria, cost ceilings, and intel-to-action accountability.
- **Not a substitute for live-evidence-first operating discipline.** Outside intel feeds the operating system; live results remain the ground truth.
- **Not a place to log every interesting paper.** Curiosity does not equal intel. The bar is "produces ≥1 operating-system change per quarter."
- **Not a permanent watchlist.** Sources retire. Books leave the queue. Tools get committed or skipped. Theater dies fast.

---

*Filed 2026-04-29 as the canonical input-lane reference. Reviewed weekly via ChatGPT Friday task; deep-triaged twice-monthly with Claude assessments; quarterly retirement + intake review. The rules are the same as the operating system: hard to game, hard to drift, cost-bounded, evidence-required.*
