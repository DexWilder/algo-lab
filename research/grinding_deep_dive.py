"""GRINDING + LOW_RV deep dive on Donchian MNQ-Long."""
import sys
import importlib.util
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

# Load Donchian
spec = importlib.util.spec_from_file_location('donchian', ROOT / 'strategies/donchian_trend/strategy.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

engine = RegimeEngine()

df = pd.read_csv(ROOT / 'data/processed/MNQ_5m.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
mod.TICK_SIZE = 0.25
signals = mod.generate_signals(df)
result = run_backtest(df, signals, mode='long', point_value=2.0, symbol='MNQ')
trades = result['trades_df']

regime_daily = engine.get_daily_regimes(df)
regime_daily['_date'] = pd.to_datetime(regime_daily['_date'])
regime_daily['_date_date'] = regime_daily['_date'].dt.date
trades['entry_date'] = pd.to_datetime(trades['entry_time']).dt.date

trades_m = trades.merge(
    regime_daily[['_date_date', 'vol_regime', 'trend_regime', 'rv_regime',
                  'trend_persistence', 'persistence_score', 'composite_regime']],
    left_on='entry_date', right_on='_date_date', how='left'
)

print('=' * 70)
print('  GRINDING + LOW_RV DEEP DIVE — Donchian MNQ-Long')
print('=' * 70)

# 1. GRINDING trades by RV regime
print('\n  GRINDING trades by RV regime:')
grinding = trades_m[trades_m['trend_persistence'] == 'GRINDING']
for rv in ['LOW_RV', 'NORMAL_RV', 'HIGH_RV']:
    subset = grinding[grinding['rv_regime'] == rv]
    if len(subset) > 0:
        pnl = subset['pnl'].sum()
        wr = (subset['pnl'] > 0).mean() * 100
        avg = subset['pnl'].mean()
        print(f'    {rv}: {len(subset)} trades, PnL=${pnl:,.0f}, WR={wr:.1f}%, AvgPnL=${avg:,.0f}')

# 2. GRINDING + target cell intersection
print('\n  GRINDING + HIGH_VOL + TRENDING + LOW_RV (intersection):')
target_grinding = trades_m[
    (trades_m['trend_persistence'] == 'GRINDING') &
    (trades_m['vol_regime'] == 'HIGH_VOL') &
    (trades_m['trend_regime'] == 'TRENDING') &
    (trades_m['rv_regime'] == 'LOW_RV')
]
if len(target_grinding) > 0:
    print(f'    Trades: {len(target_grinding)}')
    print(f'    PnL: ${target_grinding["pnl"].sum():,.0f}')
    print(f'    WR: {(target_grinding["pnl"] > 0).mean() * 100:.1f}%')
    for _, t in target_grinding.iterrows():
        print(f'      {t["entry_time"]} -> ${t["pnl"]:,.0f}')
else:
    print('    No trades in this intersection')

# 3. LOW_RV trades by persistence
print('\n  LOW_RV trades by trend persistence:')
low_rv = trades_m[trades_m['rv_regime'] == 'LOW_RV']
for p in ['GRINDING', 'CHOPPY']:
    subset = low_rv[low_rv['trend_persistence'] == p]
    if len(subset) > 0:
        pnl = subset['pnl'].sum()
        wr = (subset['pnl'] > 0).mean() * 100
        print(f'    {p}: {len(subset)} trades, PnL=${pnl:,.0f}, WR={wr:.1f}%')

# 4. Persistence score distribution for target cell trades
print('\n  Persistence score for target cell trades:')
target_all = trades_m[
    (trades_m['vol_regime'] == 'HIGH_VOL') &
    (trades_m['trend_regime'] == 'TRENDING') &
    (trades_m['rv_regime'] == 'LOW_RV')
]
if len(target_all) > 0:
    scores = target_all['persistence_score']
    print(f'    n={len(target_all)}, mean={scores.mean():.1f}, '
          f'median={scores.median():.1f}, min={scores.min():.0f}, max={scores.max():.0f}')
    for thresh in [0, 4, 8]:
        high = target_all[target_all['persistence_score'].abs() >= thresh]
        print(f'    |score| >= {thresh}: {len(high)} trades, PnL=${high["pnl"].sum():,.0f}')

# 5. Does GRINDING fix the bleed?
print('\n  DOES GRINDING FIX THE BLEED?')
print(f'    Target cell (all): {len(target_all)} trades, '
      f'PnL=${target_all["pnl"].sum():,.0f}')
choppy_target = target_all[target_all['trend_persistence'] == 'CHOPPY']
grind_target = target_all[target_all['trend_persistence'] == 'GRINDING']
print(f'    Target cell CHOPPY only: {len(choppy_target)} trades, '
      f'PnL=${choppy_target["pnl"].sum():,.0f}')
print(f'    Target cell GRINDING only: {len(grind_target)} trades, '
      f'PnL=${grind_target["pnl"].sum():,.0f}')

# 6. What if we skip LOW_RV entirely?
print('\n  DONCHIAN EXCLUDING LOW_RV:')
no_low_rv = trades_m[trades_m['rv_regime'] != 'LOW_RV']
low_rv_only = trades_m[trades_m['rv_regime'] == 'LOW_RV']
eq_no = pd.Series(50000 + np.cumsum(np.concatenate([[0], no_low_rv['pnl'].values])))
m = compute_extended_metrics(no_low_rv, eq_no, 2.0)
print(f'    Trades: {m["trade_count"]}, PF={m["profit_factor"]}, '
      f'Sharpe={m["sharpe"]}, PnL=${m["total_pnl"]:,.0f}')
print(f'    LOW_RV trades excluded: {len(low_rv_only)}, '
      f'PnL lost: ${low_rv_only["pnl"].sum():,.0f}')

# 7. Donchian GRINDING-only + excluding LOW_RV
print('\n  DONCHIAN GRINDING + NO LOW_RV:')
grind_no_low = trades_m[
    (trades_m['trend_persistence'] == 'GRINDING') &
    (trades_m['rv_regime'] != 'LOW_RV')
]
if len(grind_no_low) >= 10:
    eq_g = pd.Series(50000 + np.cumsum(np.concatenate([[0], grind_no_low['pnl'].values])))
    mg = compute_extended_metrics(grind_no_low, eq_g, 2.0)
    print(f'    Trades: {mg["trade_count"]}, PF={mg["profit_factor"]}, '
          f'Sharpe={mg["sharpe"]}, PnL=${mg["total_pnl"]:,.0f}')
else:
    print(f'    Only {len(grind_no_low)} trades — insufficient')
