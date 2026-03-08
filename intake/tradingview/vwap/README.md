# VWAP Mean Reversion Scripts

**Roster Target**: ALGO-CORE-VWAP-001
**Target Count**: 20 scripts
**Family**: vwap

## Status Flow

raw -> reviewed -> cleaned -> standardized -> converted -> backtested -> validated

## Review Criteria

Scripts are scored on six weighted dimensions:

1. **Testability** (25%) -- Can the script be backtested without manual intervention?
2. **Futures Fit** (20%) -- Does the logic apply to MES/MNQ/MGC futures on 3m/5m/15m?
3. **Prop Fit** (20%) -- Is the risk profile compatible with prop account rules?
4. **Clarity** (15%) -- Is the code readable and the logic well-documented?
5. **Conversion Difficulty** (10%) -- How much work to convert to Python/backtest engine?
6. **Diversification Potential** (10%) -- Does it add a unique edge vs existing strategies?

## Key Filters

- Must have clear, programmable entry and exit rules
- No repaint (no future data references, closed bars only)
- Futures compatible (works on MES, MNQ, MGC, or similar micro futures)
- VWAP deviation/band logic must be explicit, not discretionary
