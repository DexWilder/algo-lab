# FQL Governance Audit — 2026-05-07

**Generated:** 2026-05-07T21:41:18
**Scope:** evidence absorption + review load + Lane B self-healing + cost-of-evidence
**Safety:** report-only; no mutation of any surface

**Overall posture:** 🔴 **RED**  |  Risks: 5  |  Actions surfaced: 2

---

## Summary — actions surfaced

1. STOP building; consolidate, review, and absorb before adding new modules
2. Roadmap: extend tripwire/self-halt pattern from forge-daily-loop to 9 agents that lack it

---

## 1. Evidence Absorption Status

### Counts (lookback 7d)

- Forge fires in window: **3**
- distinct PASS candidates: **8**
  - already in registry: 8 ✅
  - **pending review (not in registry): 0**
- daily Forge reports on disk: 3
- repeated PASS-tests of already-registered candidates: 8

### Backlog status: 🟢 **GREEN**
- thresholds: GREEN ≤ 5 / YELLOW ≤ 15 / RED > 15

### Repeated-already-registered diagnostic

- 8 candidate-tests in window are RE-TESTING already-registered candidates.
- Not a problem at low counts (cross-validation), but if same candidate is hit >3× without verdict change, prune from rotation.
  - `XB-PB-EMA-Ladder-MCL`: 1 re-tests
  - `XB-PB-EMA-Ladder-MYM`: 1 re-tests
  - `XB-BB-EMA-Ladder-MGC`: 1 re-tests
  - `XB-BB-EMA-Ladder-MCL`: 1 re-tests
  - `XB-BB-EMA-Ladder-MYM`: 1 re-tests

---

## 2. Operator Review Load Score

### Review Load Score (lookback 7d)

**Total score: 49**

| Class | Weight | Count | Subtotal |
|---|---:|---:|---:|
| report | 1 | 26 | 26 |
| preflight | 2 | 1 | 2 |
| registry_proposal | 3 | 2 | 6 |
| automation_activation | 5 | 3 | 15 |
| lane_a_change | 5 | 0 | 0 |

- commits in window: 32

### Density: 🔴 **RED — operator overload risk**
- bands (7d window): GREEN <15 / YELLOW 15-34 / RED ≥35  *(tunable via `REVIEW_WEIGHTS`)*

### Notable items in window

**automation_activation** (3):
- `ad6ad38` Fix Phase B activation: python path + digest filename convention
- `060012f` Phase B activation: com.fql.forge-daily-loop loaded and scheduled
- `31d7721` Lane B / Forge: Phase B activation pre-flight (plist bug fixed)

**registry_proposal** (2):
- `a5d75a1` Batch register 2026-05-06 — append 12 Forge hybrid candidates
- `d65c852` Lane B / Forge: prune KILL'd candidate + batch register pre-flight (14 PASSes)

**preflight** (1):
- `a95ac91` Lane B / Forge: source-priority patch pre-flight (closed-loop tier 2)

---

## 3. Lane B Self-Healing Audit

### Per-agent self-healing posture

| Agent | Loaded | Tripwire mechanism | Last log age | Output health |
|---|:---:|:---:|---|:---:|
| `ai.openclaw.gateway` | ✅ | — | — | — |
| `com.fql.watchdog` | ✅ | ✅ | 0.1h | ✅ |
| `com.fql.claw-control-loop` | ✅ | — | (no logs) | ⚠️ |
| `com.fql.forward-day` | ✅ | — | (no logs) | ⚠️ |
| `com.fql.daily-research` | ✅ | — | 3.9h | ✅ |
| `com.fql.operator-digest` | ✅ | — | (no logs) | ⚠️ |
| `com.fql.twice-weekly-research` | ✅ | — | 3.5h | ✅ |
| `com.fql.weekly-research` | ✅ | — | 6.1d | ✅ |
| `com.fql.source-helpers` | ✅ | — | 1.1d | ✅ |
| `com.fql.treasury-rolldown-monthly` | ✅ | ✅ | 4.5h | ✅ |
| `com.fql.forge-daily-loop` | ✅ | ✅ | 2.7h | ✅ |
| `com.fql.forge-morning-digest` | ✅ | — | 13.7h | ✅ |
| `com.fql.monthly-system-review` | ✅ | — | (no logs) | ⚠️ |

### Agents WITHOUT tripwire mechanism (9)

- `com.fql.claw-control-loop`
- `com.fql.forward-day`
- `com.fql.daily-research`
- `com.fql.operator-digest`
- `com.fql.twice-weekly-research`
- `com.fql.weekly-research`
- `com.fql.source-helpers`
- `com.fql.forge-morning-digest`
- `com.fql.monthly-system-review`

---

## 4. Cost-of-Evidence Instrumentation

### Forge fires in window: 3

- total runtime: **220.4s**
- candidates tested: **15**
- avg runtime per candidate: **14.7s**
- avg candidates per fire: 5.0

### Placeholder cost

- assumes $0.001/s (rough placeholder; replace when actual cost data available)
- estimated window cost: **$0.2204**
- per-fire cost: $0.0735
- per-candidate cost: $0.0147

### Per-fire detail

| Date | Runtime (s) | Candidates | s/candidate |
|---|---:|---:|---:|
| 2026-05-05 | 74.3 | 5 | 14.9 |
| 2026-05-06 | 63.0 | 5 | 12.6 |
| 2026-05-07 | 83.1 | 5 | 16.6 |

### Trend

- recent (last 3 fires) avg runtime: 73.5s

### Cadence-escalation gate suggestions (for future #10)

- HALT escalation if avg runtime > 240s (trending toward 5min tripwire)
- HALT escalation if per-candidate runtime > 30s (cheap-screen no longer cheap)
- HALT escalation if placeholder cost projects > $10/month at proposed cadence

---
