"""P20 — crypto funding/carry (reconcile UNUSED feeds okx_BTC_USD_SWAP, deribit_ETH_PERPETUAL; DVOL_ETH malformed) report-only."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
print("=== P20 crypto funding/carry (reconcile unused feeds) ===")
res=[]
try:
    okx=pd.read_csv(ROOT/"data/feeds/okx_BTC_USD_SWAP.csv"); okx["day"]=pd.to_datetime(okx["day"])
    okx=okx.sort_values("day"); ret=okx["close"].pct_change().shift(-1)        # next-day return
    pos=-np.sign(okx["funding"])                                               # funding>0 -> shorts get paid -> short
    pnl=(pos*ret).dropna(); sh=round(pnl.mean()/pnl.std()*np.sqrt(365),2) if pnl.std()>0 else 0
    print(f"  okx BTC funding-carry: n={len(pnl)} annSh={sh} cumret={pnl.sum()*100:.0f}%"); res.append(("okx_funding",sh)); record("P20_crypto_funding",asset="BTC",sharpe=sh,verdict="screen")
except Exception as e: print(f"  okx: DATA_LIMITED {e}")
try:
    eth=pd.read_csv(ROOT/"data/feeds/deribit_ETH_PERPETUAL.csv"); eth["day"]=pd.to_datetime(eth["day"]); eth=eth.sort_values("day")
    ret=eth["px"].pct_change().shift(-1); pos=np.sign(eth["carry"])
    pnl=(pos*ret).dropna(); sh=round(pnl.mean()/pnl.std()*np.sqrt(365),2) if pnl.std()>0 else 0
    print(f"  ETH carry: n={len(pnl)} annSh={sh}"); res.append(("eth_carry",sh)); record("P20_crypto_carry",asset="ETH",sharpe=sh,verdict="screen")
except Exception as e: print(f"  eth: DATA_LIMITED {e}")
print("  deribit_DVOL_ETH.csv: malformed (no header) -> DATA_LIMITED (flag for re-pull)")
best=max([s for _,s in res],default=0)
print(f"VERDICT: {'review' if abs(best)>0.8 else 'CLEAN_KILL/DATA_LIMITED'} (N={count()})")
