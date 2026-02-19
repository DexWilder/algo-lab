"""Ranking score computation for strategy comparison."""


def compute_score(metrics: dict) -> float:
    """Compute a composite ranking score from strategy metrics.

    Formula (temporary — will be refined with real data):
        score = (roi * 0.4) + (sharpe * 0.3) - (max_drawdown * 0.2) + (ev * 0.1)

    Note: Values are not yet normalized across strategies. Once we have
    multiple strategies with real results, normalization (z-score or min-max)
    should be applied before weighting.

    Parameters
    ----------
    metrics : dict
        Must contain keys: roi, max_drawdown, sharpe, expected_value.

    Returns
    -------
    float
        Composite score (higher is better).
    """
    score = (
        (metrics["roi"] * 0.4)
        + (metrics["sharpe"] * 0.3)
        - (metrics["max_drawdown"] * 0.2)
        + (metrics["expected_value"] * 0.1)
    )
    return round(score, 4)
