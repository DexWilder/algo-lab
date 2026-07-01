"""STRATEGY-EXPRESSION VALIDATOR (2026-07-01) — PRE-TEST gate. Catches degenerate/leaky expressions BEFORE a verdict.
Would have caught the rates carry-sign degeneracy (~always long duration). Call assert_expression_valid(pos, pnl, label)
in every family sprint before recording a result. Returns (ok, flags)."""
import numpy as np, pandas as pd
def validate_expression(position, pnl, label="expr", intended_side=None, min_trades=30):
    pos=pd.Series(position).dropna(); p=pd.Series(pnl).dropna(); flags=[]
    n=len(pos)
    if n<min_trades: flags.append(f"SAMPLE_FLOOR n={n}<{min_trades}")
    # constant / near-constant signal
    if pos.nunique()<=1 or pos.std()==0: flags.append("CONSTANT_SIGNAL")
    # side distribution (the degenerate-carry catch)
    lo=float((pos>0).mean()); sh=float((pos<0).mean()); fl=float((pos==0).mean())
    active=lo+sh
    if active>0 and max(lo,sh)/active>0.90 and intended_side is None:
        flags.append(f"DEGENERATE_SIDE long={lo:.0%} short={sh:.0%} flat={fl:.0%} (>90% one side; is this a real signal or just directional beta?)")
    # turnover
    turn=float(pos.diff().abs().sum())
    if turn<=0: flags.append("ZERO_TURNOVER")
    ntrades=int((pos.diff().abs()>0).sum())
    if ntrades<min_trades: flags.append(f"FEW_TRADES {ntrades}")
    # concentration by year
    if len(p)>60:
        yr=p.groupby(pd.DatetimeIndex(p.index).year).sum() if isinstance(p.index,pd.DatetimeIndex) else None
        if yr is not None and p.sum()>0:
            maxyr=100*yr.max()/p.sum()
            if maxyr>60: flags.append(f"YEAR_CONCENTRATION max-year={maxyr:.0f}%>60% (one year drives it)")
    ok=not any(f.split()[0] in ("CONSTANT_SIGNAL","DEGENERATE_SIDE","ZERO_TURNOVER") for f in flags)
    return ok, flags, dict(long=lo,short=sh,flat=fl,trades=ntrades)
def assert_expression_valid(position, pnl, label="expr", intended_side=None, min_trades=30):
    ok,flags,d=validate_expression(position,pnl,label,intended_side,min_trades)
    tag="EXPR_OK" if ok else "EXPR_INVALID"
    print(f"  [expr-validate {label}] {tag} side(L/S/flat)={d['long']:.0%}/{d['short']:.0%}/{d['flat']:.0%} trades={d['trades']}" + ("" if not flags else " | "+"; ".join(flags)))
    return ok
if __name__=="__main__":
    import numpy as np
    idx=pd.date_range("2020-01-01",periods=500)
    print("degenerate (always long):"); assert_expression_valid(pd.Series(np.ones(500),index=idx), pd.Series(np.random.randn(500),index=idx),"always_long")
    print("healthy:"); assert_expression_valid(pd.Series(np.sign(np.random.randn(500)),index=idx), pd.Series(np.random.randn(500),index=idx),"balanced")
