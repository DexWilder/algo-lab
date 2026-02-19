"""Prop firm rule evaluation — Phase 3 implementation."""


def evaluate_prop(
    stats: dict,
    equity_curve: "pd.Series",
    mode: str = "apex_50k",
) -> dict:
    """Evaluate backtest results against prop firm rules.

    Parameters
    ----------
    stats : dict
        Backtest statistics from run_backtest().
    equity_curve : pd.Series
        Equity curve from run_backtest().
    mode : str
        Prop firm rule set to evaluate against. Default: 'apex_50k'.

    Returns
    -------
    dict
        Keys: passed (bool), rules (dict of rule -> pass/fail), details (str).

    Raises
    ------
    NotImplementedError
        Phase 3 — not yet implemented.

    Notes
    -----
    Apex 50K Evaluation Rules (to be implemented):
    - Account size: $50,000
    - Profit target: $3,000
    - Trailing drawdown: $2,500 (trails from highest equity, never below starting balance)
    - Daily loss limit: None (Apex does not have a daily loss limit)
    - Max contracts: 10 MES (or 2 ES)
    - Trading hours: CME Globex hours only
    - Minimum trading days: 7
    - No trading during major news events (optional rule)
    """
    raise NotImplementedError(
        "evaluate_prop() is a Phase 3 feature. "
        "See docs/ROADMAP.md for implementation plan."
    )
