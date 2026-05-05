# VWAP Cross-Asset Confirmation — Was VWAP Universally Weak? (2026-05-05)

**Filed:** 2026-05-05 (operator's option 1 closeout test)
**Authority:** T1 Lane B / Forge — no Lane A surfaces touched, no registry mutation.
**Question:** Was VWAP entry only weak on MNQ, or broadly weak as XB-trio entry?

---

## Result

| Asset | n | PF | Net PnL | Max DD | Verdict |
|---|---:|---:|---:|---:|---|
| MNQ (yesterday baseline — KILL) | 812 | 1.056 | +$2,511 | -$5,212 | KILL |
| MES | 881 | 1.097 | +$2,599 | -$3,544 | WATCH |
| **MGC** | **368** | **1.219** | **+$2,669** | **-$1,870** | **PASS** |
| **MCL** | **502** | **1.283** | **+$3,207** | **-$1,407** | **PASS** |
| **MYM** | **271** | **1.488** | **+$3,164** | **-$637** | **PASS** |

**VWAP is MNQ-specific weakness, not universal.** 3 of 4 alternative assets PASS; only MNQ + (marginally) MES underperform.

---

## Architecture answer

**VWAP retention decision:** keep as a viable entry — asset-specific. NOT killed globally. Use it on MGC / MCL / MYM where it works; avoid it on MNQ where it's the wrong entry for that asset's microstructure.

**This is a major correction to yesterday's interpretation.** I concluded after the MNQ test that "VWAP doesn't work in the proven trio." Wrong. The correct conclusion: "VWAP doesn't work *on MNQ* in the proven trio." MNQ specifically is harsh on VWAP-style entries; other assets are not.

---

## Combined entry × asset matrix (today's evidence)

| Entry / Asset | MNQ | MES | MGC | MCL | MYM |
|---|---|---|---|---|---|
| ORB (registry baseline) | **1.62 PASS** | — | — | — | — |
| PB | **1.403 PASS** | 1.151 WATCH | 1.194 WATCH | **1.311 PASS** | **1.351 PASS** |
| BB | **1.245 PASS** | 1.123 WATCH | **1.522 PASS** | **1.232 PASS** | **1.785 PASS** |
| **VWAP** | **1.056 KILL** | 1.097 WATCH | **1.219 PASS** | **1.283 PASS** | **1.488 PASS** |

**Patterns visible:**
1. **MNQ is harsh on alternative entries** — 3/3 alts (PB, BB, VWAP) PASS on MNQ but VWAP specifically fails. ORB's 1.62 is the dominant entry on MNQ.
2. **MES is universally WATCH-only** — no entry alternative reaches PASS on MES; the asset itself may be the limiting factor
3. **MGC, MCL, MYM are entry-tolerant** — multiple entries PASS on each. MYM in particular shows VERY strong PFs across entries (1.351, 1.785, 1.488).
4. **The proven trio's portability is asset-conditional** — works broadly across entries on most assets; some assets (MES) are weak; some entries (VWAP) are weak on specific assets (MNQ).

**Donor catalog refinement:** entries should carry per-asset compatibility notes, not a single "viable" or "not viable" flag. `vwap_continuation` viable on MGC/MCL/MYM; not viable on MNQ.

---

## Day cumulative now

**31 candidate evaluations today.** Verdict distribution:
- **12 PASS** (8 cross-asset workhorses + HYB-VolMan + 3 new VWAP-cross-asset)
- **6 WATCH** (XB-PB-MES, XB-PB-MGC, XB-BB-MES, XB-VWAP-MES + ema_slope alt session_afternoon + HYB-FX 1.5×/1.0×)
- **11 KILL** (HYB-FX 0.75×, XB-VWAP-MNQ, HYB-CashClose A+B, HYB-LunchComp A+B, 4 ema_slope alts)
- **2 RETEST** (Donchian engine bug)

Operator-review-eligible PASSes (post-this-batch): **12 candidates**.

---

## Recommended next move

Per operator's earlier guidance: **"At this point, the value is not just more tests. The value is making sure the winners are captured cleanly."**

Proceeding to build the operator-review packet for the 12 PASS candidates so they're ready for the registry-append decision.

---

*Filed 2026-05-05. Lane B / Forge. No Lane A surfaces touched.*
