# Runner: P22_btc_funding_hostile (research/forge_cycle_P22_btc_funding_hostile.py)

```
=== P22 crypto-carry HOSTILE audit (separate lane; default KILL) ===
  BTC funding-carry (10bps fee): n=98 annSh=2.76 H1=1.98 H2=3.57 worst-day=-4.4%
  ETH carry (10bps fee): n=2365 annSh=-0.22
  deribit_DVOL_ETH.csv: malformed -> EXCLUDED (flag re-pull).
  pooled annSh=-0.16 | DSR global-N=1059 | DSR crypto-lane-N=4: 0.0013 -> DSR_FAIL_likely_overfit
HOSTILE VERDICT: separate crypto-carry lane; needs funding-timestamp precision + tail/liquidation + walk-forward before ANY belief.
STATUS: RETEST_REQUIRED (small-n/crowded; NOT a candidate, NOT prop-futures)

```
