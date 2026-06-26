"""TR7 — nfp_level_breakout (MNQ) edge audit + treasury_rolldown causality probe (report-only).
nfp: 5m-aligned, 83 sparse events -> harness causality (slice w/ events) + run_backtest edge + tail metrics.
treasury: monthly carry spread -> inspect generate_spread_signals for point-in-time carry. Classify per taxonomy."""
import sys, importlib.util, inspect
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.causality_audit import audit_signal_causality
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/f"strategies/{name}/strategy.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
# ---- nfp ----
print("=== TR7a nfp_level_breakout (MNQ) ===")
nfp=load("nfp_level_breakout"); cfg=get_asset("MNQ")
df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"]); df["date"]=df["datetime"].dt.date
def nfpsig(frame):
    fr=frame.copy(); fr["date"]=pd.to_datetime(fr["datetime"]).dt.date
    for call in (lambda: nfp.generate_signals(fr,asset="MNQ",mode="both"),lambda:nfp.generate_signals(fr,"MNQ"),lambda:nfp.generate_signals(fr)):
        try: return call()
        except TypeError: continue
    return nfp.generate_signals(fr)
sl=df.iloc[-200000:].reset_index(drop=True)  # ~17 NFP events for causality coverage
rc=audit_signal_causality(sl, lambda f: nfpsig(f)[["signal"]], "nfp_level_breakout", n_splits=8)
sig=nfpsig(df)
def edge(commission,slip):
    r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=commission,slippage_ticks=slip); return r["trades_df"]
t0=edge(0,0); t=edge(cfg["commission_per_side"],cfg["slippage_ticks"])
print(f"  cost: 0=${t0['pnl'].sum():.0f} vs costed=${t['pnl'].sum():.0f} trades={len(t)} -> {'COST_WIRED' if abs(t0['pnl'].sum()-t['pnl'].sum())>1 else 'CHECK'}")
if len(t)>=5:
    pnl=t["pnl"].values; pos_frac=100*(pnl>0).mean(); PF=pnl[pnl>0].sum()/max(-pnl[pnl<0].sum(),1)
    maxinst=100*np.sort(pnl)[-1]/pnl.sum() if pnl.sum()>0 else 0
    print(f"  TAIL-ENGINE metrics: n={len(t)} PF={PF:.2f} net=${pnl.sum():.0f} median=${np.median(pnl):.0f} pos_frac={pos_frac:.0f}% max_single_instance={maxinst:.0f}% (gate <35%)")
    print(f"  verdict inputs: causality={rc['verdict']}, n={len(t)}(<500 tail), PF, concentration -> classify in report")
else:
    print(f"  n={len(t)} trades -> insufficient; DATA_LIMITED")
# ---- treasury causality probe ----
print("\n=== TR7b treasury_rolldown_carry — carry-lineage probe ===")
tr=load("treasury_rolldown_carry"); src=inspect.getsource(tr)
shifts=src.count(".shift("); monthend=("is_month_end" in src) or ("month" in src.lower())
print(f"  static probe: .shift() uses={shifts}, month-boundary logic={monthend}")
print(f"  carry uses prior-period data? -> needs RUN of generate_spread_signals + point-in-time check of carry ranking date.")
try:
    sp=tr.generate_spread_signals()
    print(f"  generate_spread_signals -> type {type(sp).__name__}, {('len '+str(len(sp))) if hasattr(sp,'__len__') else ''}")
    print(f"  VERDICT: treasury needs bespoke multi-asset spread point-in-time harness (carry ranking at rebalance must use t-1 data). RETEST_REQUIRED_BESPOKE.")
except Exception as e:
    print(f"  generate_spread_signals error: {type(e).__name__}: {e} -> RETEST_REQUIRED_BESPOKE (interface)")
