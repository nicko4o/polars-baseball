from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import polars as pl

from polars_baseball import batting, people, pitching, standings, statcast

from .models import BenchmarkDimensions

DEFAULT_START = "2024-04-01"
DEFAULT_END = "2024-04-07"


@dataclass(frozen=True)
class BenchmarkProfile:
    name: str
    dimensions: BenchmarkDimensions
    fn: Callable[..., Awaitable[pl.DataFrame | list[pl.DataFrame]]]
    kwargs: dict[str, object]

    def to_kwargs(self) -> dict[str, object]:
        return dict(self.kwargs)


PROFILES: dict[str, BenchmarkProfile] = {
    "statcast_1day": BenchmarkProfile(
        name="statcast_1day",
        dimensions=BenchmarkDimensions(
            api="statcast",
            start_date="2024-04-01",
            end_date="2024-04-01",
            parallel=True,
            cache_state="cold",
        ),
        fn=statcast,
        kwargs={
            "start_dt": "2024-04-01",
            "end_dt": "2024-04-01",
            "parallel": True,
            "concurrency_limit": 5,
        },
    ),
    "statcast_1week": BenchmarkProfile(
        name="statcast_1week",
        dimensions=BenchmarkDimensions(
            api="statcast",
            start_date=DEFAULT_START,
            end_date=DEFAULT_END,
            parallel=True,
            cache_state="cold",
        ),
        fn=statcast,
        kwargs={
            "start_dt": DEFAULT_START,
            "end_dt": DEFAULT_END,
            "parallel": True,
            "concurrency_limit": 5,
        },
    ),
    "statcast_serial": BenchmarkProfile(
        name="statcast_serial",
        dimensions=BenchmarkDimensions(
            api="statcast",
            start_date=DEFAULT_START,
            end_date=DEFAULT_END,
            parallel=False,
            cache_state="cold",
        ),
        fn=statcast,
        kwargs={
            "start_dt": DEFAULT_START,
            "end_dt": DEFAULT_END,
            "parallel": False,
        },
    ),
    "statcast_warm": BenchmarkProfile(
        name="statcast_warm",
        dimensions=BenchmarkDimensions(
            api="statcast",
            start_date=DEFAULT_START,
            end_date=DEFAULT_END,
            parallel=True,
            cache_state="warm",
        ),
        fn=statcast,
        kwargs={
            "start_dt": DEFAULT_START,
            "end_dt": DEFAULT_END,
            "parallel": True,
            "concurrency_limit": 5,
        },
    ),
    "lahman_batting": BenchmarkProfile(
        name="lahman_batting",
        dimensions=BenchmarkDimensions(
            api="lahman",
            start_date="all",
            end_date="all",
            cache_state="cold",
        ),
        fn=batting,
        kwargs={},
    ),
    "lahman_pitching": BenchmarkProfile(
        name="lahman_pitching",
        dimensions=BenchmarkDimensions(
            api="lahman",
            start_date="all",
            end_date="all",
            cache_state="cold",
        ),
        fn=pitching,
        kwargs={},
    ),
    "lahman_people": BenchmarkProfile(
        name="lahman_people",
        dimensions=BenchmarkDimensions(
            api="lahman",
            start_date="all",
            end_date="all",
            cache_state="cold",
        ),
        fn=people,
        kwargs={},
    ),
    "standings_2024": BenchmarkProfile(
        name="standings_2024",
        dimensions=BenchmarkDimensions(
            api="standings",
            start_date="2024",
            end_date="2024",
            cache_state="cold",
        ),
        fn=standings,
        kwargs={"season": 2024},
    ),
}
