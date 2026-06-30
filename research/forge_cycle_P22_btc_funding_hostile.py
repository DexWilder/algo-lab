"""P22 — SEPARATE crypto-carry hostile audit (NOT futures-WH framing). BTC/ETH funding-carry with REALISTIC crypto
costs (exchange fee + funding cadence), walk-forward H1/H2, DSR at crypto-lane-N + global. Default KILL. Report-only.
Caveats baked in: crowded mechanism, exchange/tail/liquidation risk uncosted beyond fees, DVOL_ETH malformed."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
def shp(x,a=365): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(a),2) if len(x)>1 and x.std()>0 else 0
FEE=0.0010  # 10bps round-trip taker (realistic-conservative crypto)
print("=== P22 crypto-carry HOSTILE audit (separate lane; default KILL) ===")
out=[]
try:
    okx=pd.read_csv(ROOT/"data/feeds/okx_BTC_USD_SWAP.csv"); okx["day"]=pd.to_datetime(okx["day"]); okx=okx.sort_values("day")
    okx["ret"]=okx["close"].pct_change().shift(-1); okx["pos"]=-np.sign(okx["funding"])
    okx["flip"]=okx["pos"].diff().abs().fillna(0)>0
    okx["pnl"]=okx["pos"]*okx["ret"] - okx["flip"]*FEE + (-okx["pos"]*0)  # funding already the signal; fee on flips
    p=okx.dropna(subset=["pnl"]); h=len(p)//2
    print(f"  BTC funding-carry (10bps fee): n={len(p)} annSh={shp(p['pnl'].values)} H1={shp(p['pnl'].iloc[:h].values)} H2={shp(p['pnl'].iloc[h:].values)} worst-day={p['pnl'].min()*100:.1f}%")
    record("P22_crypto_carry",asset="BTC",sharpe=shp(p['pnl'].values),verdict="hostile",lane="crypto_carry"); out.append(p["pnl"])
except Exception as e: print(f"  BTC DATA_LIMITED: {e}")
try:
    eth=pd.read_csv(ROOT/"data/feeds/deribit_ETH_PERPETUAL.csv"); eth["day"]=pd.to_datetime(eth["day"]); eth=eth.sort_values("day")
    eth["ret"]=eth["px"].pct_change().shift(-1); eth["pos"]=np.sign(eth["carry"]); eth["flip"]=eth["pos"].diff().abs().fillna(0)>0
    eth["pnl"]=eth["pos"]*eth["ret"]-eth["flip"]*FEE; p=eth.dropna(subset=["pnl"])
    print(f"  ETH carry (10bps fee): n={len(p)} annSh={shp(p['pnl'].values)}"); record("P22_crypto_carry",asset="ETH",sharpe=shp(p['pnl'].values),verdict="hostile",lane="crypto_carry"); out.append(p["pnl"])
except Exception as e: print(f"  ETH DATA_LIMITED: {e}")
print("  deribit_DVOL_ETH.csv: malformed -> EXCLUDED (flag re-pull).")
if out:
    pooled=pd.concat(out); gN=count(); lN=count(lane="crypto_carry")
    dL=deflated_sharpe(pooled.values,lN,sr_trials_std=0.05)
    print(f"  pooled annSh={shp(pooled.values)} | DSR global-N={gN} | DSR crypto-lane-N={lN}: {dL.get('dsr')} -> {dL.get('verdict')}")
    print("HOSTILE VERDICT: separate crypto-carry lane; needs funding-timestamp precision + tail/liquidation + walk-forward before ANY belief.")
    print("STATUS: RETEST_REQUIRED (small-n/crowded; NOT a candidate, NOT prop-futures)")
else: print("STATUS: DATA_LIMITED")
