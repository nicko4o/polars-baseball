from __future__ import annotations

from dataclasses import dataclass

from benchmarks.models import BaselineRecord

WALL_TIME_THRESHOLD_SIGMA: float = 3.0


@dataclass(frozen=True)
class RegressionResult:
    is_regression: bool
    current_value: float
    baseline_mean: float
    baseline_std: float
    sigma: float


def _filter_history(
    history: list[BaselineRecord],
    *,
    profile_name: str | None,
    dimensions: dict[str, object] | None,
) -> list[BaselineRecord]:
    if profile_name is not None:
        named = [record for record in history if record.get("name") == profile_name]
        if named:
            return named
    if dimensions is None:
        return history
    return [
        record
        for record in history
        if all(record.get("dimensions", {}).get(key) == value for key, value in dimensions.items() if value is not None)
    ]


def check_regression(
    current: float,
    history: list[BaselineRecord],
    *,
    metric: str = "wall_time_seconds",
    threshold_sigma: float = WALL_TIME_THRESHOLD_SIGMA,
    profile_name: str | None = None,
    dimensions: dict[str, object] | None = None,
) -> RegressionResult:
    matching = _filter_history(history, profile_name=profile_name, dimensions=dimensions)
    values: list[float] = []
    for record in matching:
        metrics = record.get("metrics")
        if metrics is not None and metric in metrics:
            values.append(float(metrics[metric]))
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
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    std = variance**0.5
    sigma = current - mean if std == 0 else (current - mean) / std
    return RegressionResult(
        is_regression=sigma > threshold_sigma,
        current_value=current,
        baseline_mean=mean,
        baseline_std=std,
        sigma=sigma,
    )
