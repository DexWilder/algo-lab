"""ARTIFACT DETECTOR LIBRARY — every bug/trap caught this session becomes a REUSABLE detector so we never get fooled the
same way twice. Import and run these against any result before trusting it. "Every run must make the machine harder to fool."
Each detector returns (flag: bool, detail: str) — flag=True means ARTIFACT/TRAP SUSPECTED.
Usage: from research.artifact_detectors import scan_result, detect_* ; scan_result({...}) -> list of fired flags."""
import numpy as np, pandas as pd

def detect_suspicious_sharpe(sharpe, n_active=None):
    """|Sharpe| > 5 (annualized) is almost always a units bug or near-constant series, not an edge."""
    if sharpe is None: return False,""
    if abs(sharpe)>5: return True, f"|Sharpe|={sharpe} >5 — likely units bug / near-constant PnL (cost-only). Caught: 1m harness fractional-vs-points bug."
    return False,""

def detect_mirror_identical(pnl_a, pnl_b, tol=1e-6):
    """Continuation and reversal (mirror strategies) with ~identical metrics => gross PnL ~0, both just paying cost = bug."""
    a,b=np.asarray(pnl_a,float),np.asarray(pnl_b,float)
    if len(a)!=len(b): return False,""
    if abs(a.sum()-b.sum())<max(1.0,abs(a.sum())*0.02) and np.sign(a.sum())==np.sign(b.sum()):
        return True, f"mirror strategies both net {a.sum():.0f}/{b.sum():.0f} (same sign) — gross~0, paying cost only. Units/signal bug."
    return False,""

def detect_cost_inert(gross_sum, net_sum, n_trades):
    """Turnover exists but cost didn't change PnL => cost not wired (FQL Evidence Law violation)."""
    if n_trades>0 and abs(gross_sum-net_sum)<1e-9: return True,"COST_INERT: turnover>0 but gross==net (cost not applied)."
    return False,""

def detect_roll_concentration(pnl, near_roll_mask, thresh=0.6):
    """>thresh of PnL within +-N days of a contract roll => stale-deferred-price / roll artifact suspected."""
    pnl=pd.Series(pnl); m=pd.Series(near_roll_mask,index=pnl.index).fillna(False).astype(bool)
    if pnl.sum()==0: return False,""
    frac=pnl[m].sum()/pnl.sum()
    if frac>thresh: return True, f"{frac:.0%} of PnL is roll-adjacent (>{thresh:.0%}) — verify far-from-roll Sharpe survives (spreadMR_GC pattern)."
    return False,""

def detect_lookahead(signal_fn, series, ks=(300,600,900,1200), factors=(3.0,0.33)):
    """Future-perturbation invariance (causality_audit Check A). Perturb bars>k; signals[:k+1] MUST be identical."""
    s=pd.Series(np.asarray(series,float)).reset_index(drop=True); base=pd.Series(signal_fn(s)).reset_index(drop=True)
    viol=0
    for k in ks:
        if k>=len(s)-2: continue
        for fac in factors:
            p=s.copy(); p.iloc[k+1:]=p.iloc[k+1:]*fac
            s2=pd.Series(signal_fn(p)).reset_index(drop=True)
            if not base.iloc[:k+1].fillna(-999).equals(s2.iloc[:k+1].fillna(-999)): viol+=1
    return (viol>0, f"LOOKAHEAD: {viol} future-perturbation violations" if viol else "causal (0 violations)")

def detect_degenerate_active_side(position, lo=0.1, hi=0.9):
    """Side balance among NON-FLAT positions (sparse tail-engines are valid; one-sided bets are not)."""
    p=pd.Series(position).fillna(0); act=p[p!=0]
    if len(act)==0: return True,"NO active positions"
    als=(act>0).mean()
    if als<lo or als>hi: return True, f"DEGENERATE active-long-share={als:.2f} (one-sided bet, not a balanced signal)."
    return False,""

def detect_sparse(position, min_active=60):
    p=pd.Series(position).fillna(0); n=int((p!=0).sum())
    if n<min_active: return True, f"SPARSE n_active={n} (<{min_active}) — tail-engine gates apply, not workhorse."
    return False,""

def detect_session_tz(session_window, expected_rth=(510,990)):
    """Detected RTH window should land near 9:30-16:30 in the data's clock; wildly off => tz/session error."""
    s,e=session_window
    if not (expected_rth[0]-120<=s<=expected_rth[1]): return True, f"SESSION/TZ suspect: detected RTH start min={s} (expected ~570 for 9:30). Verify volume profile."
    return False,""

def detect_coverage_mismatch(ranges, max_gap_days=180):
    """ranges = {sym:(start,end)}. Non-overlapping 1m windows across instruments => cross-instrument tests mix eras (artifact)."""
    starts=[pd.Timestamp(r[0]) for r in ranges.values()]; ends=[pd.Timestamp(r[1]) for r in ranges.values()]
    overlap_start,overlap_end=max(starts),min(ends)
    if overlap_end<overlap_start: return True, f"COVERAGE MISMATCH: no common window across {list(ranges)} — {[(s,str(a)[:10],str(b)[:10]) for s,(a,b) in ranges.items()]}"
    return False, f"common window {str(overlap_start)[:10]}..{str(overlap_end)[:10]}"

def detect_dsr_cliff(dsr_by_n):
    """DSR credible at small N but collapses at realistic N => multiple-testing fragility (spreadMR_GC pattern)."""
    ns=sorted(dsr_by_n);
    if len(ns)<2: return False,""
    lo,hi=dsr_by_n[ns[0]],dsr_by_n[ns[-1]]
    if lo>=0.95 and hi<0.5: return True, f"DSR CLIFF: {lo:.2f}@N={ns[0]} -> {hi:.2f}@N={ns[-1]} — multiple-testing fragile, not DSR-credible."
    return False,""

def scan_result(r):
    """Run all applicable detectors from a result dict; return fired flags. Fields optional."""
    fired=[]
    for name,args in [("suspicious_sharpe",(r.get("sharpe"),r.get("n_active"))),]:
        f,d=detect_suspicious_sharpe(*args); fired+= [f"suspicious_sharpe: {d}"] if f else []
    if "position" in r:
        f,d=detect_degenerate_active_side(r["position"]); fired+=[f"degenerate_side: {d}"] if f else []
        f,d=detect_sparse(r["position"]); fired+=[f"sparse: {d}"] if f else []
    if "session_window" in r:
        f,d=detect_session_tz(r["session_window"]); fired+=[f"session_tz: {d}"] if f else []
    if "ranges" in r:
        f,d=detect_coverage_mismatch(r["ranges"]); fired+=[f"coverage_mismatch: {d}"] if f else []
    if "dsr_by_n" in r:
        f,d=detect_dsr_cliff(r["dsr_by_n"]); fired+=[f"dsr_cliff: {d}"] if f else []
    if "pnl" in r and "near_roll_mask" in r:
        f,d=detect_roll_concentration(r["pnl"],r["near_roll_mask"]); fired+=[f"roll_concentration: {d}"] if f else []
    return fired

if __name__=="__main__":
    print("artifact detectors self-test:")
    print("  suspicious_sharpe(-12):", detect_suspicious_sharpe(-12)[0])
    print("  coverage_mismatch(MES 2024-26 vs ZN 2019-24):", detect_coverage_mismatch({"MES":("2024-03-01","2026-03-06"),"ZN":("2019-06-30","2024-02-27")}))
    print("  dsr_cliff(N9=0.99,N1782=0.0):", detect_dsr_cliff({9:0.99,1782:0.0})[0])
    print("  degenerate_side(95% long):", detect_degenerate_active_side(pd.Series([1]*95+[-1]*5))[0])
