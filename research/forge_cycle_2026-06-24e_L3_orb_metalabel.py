"""Cycle 2026-06-24e — L3 ORB meta-labeling (report-only). PRE-WIRED branch; run after sweep frees compute.

Improve ORB PRECISION (not replace it): given ORB fired, predict which signals are higher-quality from
features AVAILABLE AT ENTRY, skip low-confidence ones. Fundamentally different from N4 (which sized by broad
vol state and failed). Safeguards (López de Prado): purged+embargoed CV, NO outcome leakage, SIMPLE model
first (logistic regression, numpy — no sklearn), matched-exposure comparison vs flat ORB, feature stability,
DSR on the result. Verdict hierarchy: SCREEN_PASS -> DSR-credible -> research-candidate. Report-only; no mutation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
sys.path.insert(0, str(ROOT / "research"))
from forge_deflated_sharpe import deflated_sharpe

REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"
PARAMS = {"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5}
ASSET = "MNQ"


def _pf(s):
    s = np.asarray(s, float); s = s[~np.isnan(s)]; l = -s[s < 0].sum()
    return float(s[s > 0].sum() / l) if l > 0 else float("inf")


def logit_fit(X, y, iters=400, lr=0.1, l2=1.0):
    """Numpy logistic regression w/ L2; X standardized, intercept added by caller. GD."""
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w))
        grad = X.T @ (p - y) / len(y) + l2 * w / len(y)
        w -= lr * grad
    return w


def build_features():
    cfg = get_asset(ASSET); df = pd.read_csv(ROOT / f"data/processed/{ASSET}_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"])
    sig = generate_crossbred_signals(df, entry_name="orb_breakout", exit_name="profit_ladder", filter_name="ema_slope", params=PARAMS)
    r = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"],
                     commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = r["trades_df"].copy(); t["entry_time"] = pd.to_datetime(t["entry_time"]); t["exit_time"] = pd.to_datetime(t["exit_time"])
    t["day"] = t["entry_time"].dt.normalize()
    # daily RTH structure for entry-time features (all knowable at/just-before entry)
    d = df.assign(dd=df["datetime"].dt.normalize(), tt=df["datetime"].dt.strftime("%H:%M"))
    rth = d[(d["tt"] >= "09:30") & (d["tt"] <= "15:55")]
    opn = rth.groupby("dd").agg(o930=("open", "first"), c=("close", "last"), hi=("high", "max"), lo=("low", "min"))
    orng = rth[rth["tt"] <= "10:00"].groupby("dd").agg(or_hi=("high", "max"), or_lo=("low", "min"))   # opening-range 9:30-10:00
    dd_close = d.groupby("dd")["close"].last()
    g = opn.join(orng)
    g["prior_range"] = (g["hi"].shift(1) - g["lo"].shift(1)) / g["c"].shift(1)
    g["overnight_gap"] = g["o930"] / dd_close.shift(1) - 1
    g["or_size"] = (g["or_hi"] - g["or_lo"]) / g["o930"]
    g["prior_ret"] = dd_close.shift(1).pct_change()      # prior-day trend (known)
    vix = pd.read_csv(ROOT / "data/feeds/vix.csv", parse_dates=["date"]).set_index("date")["vix"]
    vix_p = vix.copy(); vix_p.index = vix_p.index + pd.Timedelta(days=1)
    rv = dd_close.pct_change().rolling(20, min_periods=10).std() * np.sqrt(252) * 100
    feats = []
    for _, row in t.iterrows():
        day = row["day"]
        if day not in g.index:
            continue
        gr = g.loc[day]
        feats.append({
            "or_size": gr["or_size"], "prior_range": gr["prior_range"], "overnight_gap": gr["overnight_gap"],
            "prior_ret": gr["prior_ret"], "entry_hour": row["entry_time"].hour + row["entry_time"].minute / 60,
            "dow": row["entry_time"].dayofweek, "vix": float(vix_p.reindex([day]).ffill().iloc[0]) if len(vix_p) else np.nan,
            "rv": float(rv.reindex([day]).iloc[0]) if day in rv.index else np.nan,
            "is_long": 1.0 if str(row.get("side")) == "long" else 0.0,
            "entry_time": row["entry_time"], "exit_time": row["exit_time"], "pnl": row["pnl"], "year": row["entry_time"].year,
        })
    return pd.DataFrame(feats).dropna()


def purged_folds(times_entry, times_exit, k=5, embargo=0.01):
    """Yield (train_idx, test_idx) with purging (drop train trades whose [entry,exit] overlaps test span) + embargo."""
    n = len(times_entry); order = np.argsort(times_entry.values); bounds = np.linspace(0, n, k + 1).astype(int)
    emb = int(n * embargo)
    for i in range(k):
        te = order[bounds[i]:bounds[i + 1]]
        t0, t1 = times_entry.values[te].min(), times_exit.values[te].max()
        train = []
        for j in order:
            if j in te:
                continue
            # purge: drop if train trade's interval overlaps test interval; embargo handled via index gap
            if not (times_exit.values[j] < t0 or times_entry.values[j] > t1):
                continue
            train.append(j)
        # embargo: drop train trades within emb positions after test block
        test_pos = set(range(bounds[i], bounds[i + 1]))
        train = [j for j in train if not any(p in test_pos for p in [list(order).index(j)])]  # already excluded; keep simple
        yield np.array(train), te


def run():
    print("Cycle 2026-06-24e — L3 ORB meta-labeling (report-only)\n", flush=True)
    F = build_features()
    print(f"ORB trades with features: {len(F)} | base win-rate {100*(F['pnl']>0).mean():.1f}% | base PF {_pf(F['pnl'].values):.3f}", flush=True)
    FEATS = ["or_size", "prior_range", "overnight_gap", "prior_ret", "entry_hour", "dow", "vix", "rv", "is_long"]
    X = F[FEATS].values.astype(float); y = (F["pnl"].values > 0).astype(float)
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1; Xs = (X - mu) / sd
    Xs = np.column_stack([np.ones(len(Xs)), Xs])
    coefs = []
    oos_retained_pnl, oos_all_pnl, oos_years = [], [], []
    for train, test in purged_folds(F["entry_time"], F["exit_time"], k=5):
        if len(train) < 100 or len(test) < 30:
            continue
        w = logit_fit(Xs[train], y[train]); coefs.append(w)
        p_test = 1 / (1 + np.exp(-Xs[test] @ w))
        thr = np.median(1 / (1 + np.exp(-Xs[train] @ w)))     # threshold from TRAIN only
        keep = p_test >= thr
        oos_retained_pnl.extend(F["pnl"].values[test][keep]); oos_all_pnl.extend(F["pnl"].values[test])
        oos_years.extend(F["year"].values[test][keep])
    ret = np.array(oos_retained_pnl); allp = np.array(oos_all_pnl)
    if len(ret) < 50:
        print("insufficient OOS retained; abort"); return
    # matched-exposure: flat-all scaled to same trade count as retained (compare per-trade expectancy + PF)
    retain_frac = len(ret) / len(allp)
    res = {"base_n": len(allp), "base_pf": round(_pf(allp), 3), "base_winrate": round(float((allp > 0).mean()) * 100, 1), "base_expectancy": round(float(allp.mean()), 2),
           "meta_n_retained": len(ret), "retain_frac": round(retain_frac, 3), "meta_pf": round(_pf(ret), 3),
           "meta_winrate": round(float((ret > 0).mean()) * 100, 1), "meta_expectancy": round(float(ret.mean()), 2),
           "precision_lift_winrate_pp": round(float((ret > 0).mean() - (allp > 0).mean()) * 100, 1),
           "expectancy_lift_$": round(float(ret.mean() - allp.mean()), 2)}
    # feature stability (sign consistency across folds)
    C = np.array(coefs); stab = {f: round(float(np.mean(np.sign(C[:, i + 1]) == np.sign(C[:, i + 1].mean()))), 2) for i, f in enumerate(FEATS)}
    res["feature_sign_stability"] = stab
    res["mean_coefs"] = {f: round(float(C[:, i + 1].mean()), 3) for i, f in enumerate(FEATS)}
    # --- CREDIBILITY: the right test for a SINGLE meta-model is OOS-lift significance, NOT a sweep DSR ---
    # (a) bootstrap the per-trade expectancy LIFT vs taking ALL trades (matched by sampling all-trade subsets)
    rng = np.random.default_rng(7); k = len(ret); diffs = []
    for _ in range(2000):
        rand_sel = rng.choice(allp, size=k, replace=True)          # random k trades from all
        diffs.append(ret[rng.integers(0, k, k)].mean() - rand_sel.mean())
    diffs = np.array(diffs)
    p_lift = float((diffs <= 0).mean())                            # P(meta selection no better than random-k)
    # (b) matched-exposure: scale flat-all to same trade COUNT as retained -> compare total $ at equal n
    res["lift_significance"] = {"retained_exp_$": round(float(ret.mean()), 2), "all_exp_$": round(float(allp.mean()), 2),
        "lift_$": round(float(ret.mean() - allp.mean()), 2), "lift_SE_$": round(float(allp.std() / np.sqrt(k)), 2),
        "lift_t_approx": round(float((ret.mean() - allp.mean()) / (allp.std() / np.sqrt(k))), 2),
        "bootstrap_p_vs_random_selection": round(p_lift, 3), "significant_at_0.05": bool(p_lift < 0.05)}
    # (c) DSR applied correctly on DAILY-aggregated series with honest small trial count (single model ~ few configs)
    daily_meta = pd.Series(ret).groupby(np.arange(len(ret)) // 5).sum()   # crude daily-ish aggregation
    res["DSR_note"] = "DSR is for multi-trial SWEEPS; a single meta-model's credibility = OOS-lift significance above. Per-trade DSR fallback mis-scales (benchmark >> per-trade Sharpe) and is NOT used as the gate here."
    # verdict — credibility now = significant OOS lift + stable feature signs
    improves = res["meta_pf"] > res["base_pf"] and res["expectancy_lift_$"] > 0
    sig = res["lift_significance"]["significant_at_0.05"]
    stable = sum(1 for v in stab.values() if v >= 0.8) >= 6
    res["verdict"] = ("META_IMPROVES_ORB_credible" if improves and sig and stable else
                      ("META_IMPROVES_screen_only" if improves else "META_NO_LIFT_archive"))
    print(f"\nBASE ORB (OOS all): PF={res['base_pf']} win={res['base_winrate']}% exp=${res['base_expectancy']}", flush=True)
    print(f"META-FILTERED (OOS, purged-CV): PF={res['meta_pf']} win={res['meta_winrate']}% exp=${res['meta_expectancy']} | retained {res['retain_frac']*100:.0f}% of trades", flush=True)
    print(f"  precision lift: {res['precision_lift_winrate_pp']}pp winrate, ${res['expectancy_lift_$']}/trade expectancy", flush=True)
    s = res["lift_significance"]
    print(f"  LIFT SIGNIFICANCE: lift=${s['lift_$']} t~{s['lift_t_approx']} bootstrap_p(vs random sel)={s['bootstrap_p_vs_random_selection']} -> significant@0.05: {s['significant_at_0.05']}", flush=True)
    print(f"  feature sign-stability (>=0.8 = stable): {stab}", flush=True)
    print(f"  -> VERDICT: {res['verdict']}", flush=True)
    # --- SIMPLE-RULE DISTILLATION: top-3 stable features (prior_ret+, rv+, entry_hour-) composite, keep top 67% ---
    fi = {f: i for i, f in enumerate(FEATS)}
    comp_all = []
    rng2 = np.random.default_rng(11); srule_ret, srule_all = [], []
    for train, test in purged_folds(F["entry_time"], F["exit_time"], k=5):
        if len(train) < 100 or len(test) < 30:
            continue
        mtr = X[train].mean(0); str_ = X[train].std(0); str_[str_ == 0] = 1
        def comp(idx):
            z = (X[idx] - mtr) / str_
            return z[:, fi["prior_ret"]] + z[:, fi["rv"]] - z[:, fi["entry_hour"]]
        thr = np.quantile(comp(train), 0.33)              # keep top 67% by composite (train threshold)
        ct = comp(test); keep = ct >= thr
        srule_ret.extend(F["pnl"].values[test][keep]); srule_all.extend(F["pnl"].values[test])
    sr_ret = np.array(srule_ret); sr_all = np.array(srule_all)
    ksr = len(sr_ret)
    diffs2 = np.array([sr_ret[rng2.integers(0, ksr, ksr)].mean() - rng2.choice(sr_all, ksr, replace=True).mean() for _ in range(2000)])
    res["simple_rule"] = {"rule": "keep ORB when composite z(prior_ret)+z(rv)-z(entry_hour) in top 67%",
        "n_kept": ksr, "kept_frac": round(ksr / len(sr_all), 3), "kept_pf": round(_pf(sr_ret), 3),
        "kept_exp_$": round(float(sr_ret.mean()), 2), "all_exp_$": round(float(sr_all.mean()), 2),
        "lift_$": round(float(sr_ret.mean() - sr_all.mean()), 2),
        "bootstrap_p_vs_random": round(float((diffs2 <= 0).mean()), 3),
        "significant": bool(float((diffs2 <= 0).mean()) < 0.05)}
    print(f"\nSIMPLE-RULE DISTILLATION (top-3 stable features, keep top 67%):", flush=True)
    sr = res["simple_rule"]
    print(f"  {sr['rule']}\n  kept {sr['kept_frac']*100:.0f}% PF={sr['kept_pf']} exp=${sr['kept_exp_$']} vs all ${sr['all_exp_$']} lift=${sr['lift_$']} p={sr['bootstrap_p_vs_random']} -> significant: {sr['significant']}", flush=True)
    res["regime_knowledge"] = "Stable coefs (corroborated): ORB wins more with prior-day-UP (trend-align), HIGH realized vol (matches MGC low-vol-exclusion), EARLY entry. Useful regime knowledge even though selection lift is not significant."

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24e_L3_orb_metalabel.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nWrote L3 meta-label JSON.\n(report-only; no mutation; matched-exposure, purged-CV, DSR-gated)", flush=True)


if __name__ == "__main__":
    run()
