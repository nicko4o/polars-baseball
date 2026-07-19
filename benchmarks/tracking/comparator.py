from __future__ import annotations

from dataclasses import dataclass
from typing import Any

WALL_TIME_THRESHOLD_SIGMA: float = 3.0


@dataclass(frozen=True)
class RegressionResult:
    is_regression: bool
    current_value: float
    baseline_mean: float
    baseline_std: float
    sigma: float


def check_regression(
    current: float,
    history: list[dict[str, Any]],
    *,
    metric: str = "wall_time_seconds",
    threshold_sigma: float = WALL_TIME_THRESHOLD_SIGMA,
) -> RegressionResult:
    values = [r["metrics"][metric] for r in history if metric in r.get("metrics", {})]
    if len(values) < 2:
        return RegressionResult(
            is_regression=False,
            current_value=current,
            baseline_mean=current,
            baseline_std=0.0,
            sigma=0.0,
        )
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = variance**0.5
    if std == 0:
        sigma = current - mean
    else:
        sigma = (current - mean) / std
    return RegressionResult(
        is_regression=sigma > threshold_sigma,
        current_value=current,
        baseline_mean=mean,
        baseline_std=std,
        sigma=sigma,
    )
