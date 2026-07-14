"""ProviderChain + ExtractionStrategy + StructureFingerprint.

Core abstractions for multi-strategy degradation parsing with high observability.
When all strategies fail, ProviderChain raises UpstreamStructureChangedError
with full diagnostic context rather than returning a silent None result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import polars as pl

from polars_baseball.exceptions import UpstreamStructureChangedError

__all__ = [
    "ChainResult",
    "ExtractionStrategy",
    "ProbeResult",
    "ProviderChain",
    "StructureFingerprint",
]


@dataclass(frozen=True)
class StructureFingerprint:
    """Structural signature describing what content shape a parser expects.

    Attributes:
        source: Human-readable label identifying the strategy (e.g. "BRef-CSV-Export").
        required_indicators: Mandatory substrings that must be present in raw content.
    """

    source: str
    required_indicators: tuple[str, ...] = ()

    def diff(self, raw_content: str) -> str:
        """Return diagnostic string describing which indicators are missing.

        Returns empty string when all indicators are present.
        """
        missing = [ind for ind in self.required_indicators if ind not in raw_content]
        if not missing:
            return ""
        return f"[{self.source}] Missing indicators: {missing}"


@dataclass
class ProbeResult:
    """Result of probing whether a strategy can handle given raw content.

    Attributes:
        can_handle: Whether the strategy can parse this content.
        diagnostics: Human-readable explanation (especially when can_handle is False).
    """

    can_handle: bool
    diagnostics: str = ""


@runtime_checkable
class ExtractionStrategy(Protocol):
    """Single extraction strategy.

    A strategy knows:
      - Whether it can handle a given raw content (probe).
      - How to extract a DataFrame from it.
      - What structure fingerprint it expects (for diagnostics).
    """

    def can_handle(self, raw: str) -> ProbeResult:
        """Probe whether this strategy can parse the raw content."""

    def extract(self, raw: str) -> pl.DataFrame:
        """Execute extraction. Called only after can_handle returns True."""

    def fingerprint(self) -> StructureFingerprint:
        """Return the structural signature of this strategy for diagnostics."""


@dataclass
class ChainResult:
    """Container for the result of a successful ProviderChain execution.

    Attributes:
        strategy_used: Name of the strategy that succeeded.
        probe_results: Ordered list of (strategy_name, passed, diagnostics) for every strategy tried.
        df: Parsed DataFrame from the winning strategy.
    """

    strategy_used: str
    probe_results: list[tuple[str, bool, str]] = field(default_factory=list)
    df: pl.DataFrame = field(default_factory=pl.DataFrame)


class ProviderChain:
    """Orchestrates a chain of extraction strategies with graceful degradation.

    Each strategy is probed in order; the first matching strategy is used.
    If all strategies fail, raises UpstreamStructureChangedError with full
    diagnostic context (fail-fast, never returns a silent None result).
    """

    def __init__(self, strategies: list[ExtractionStrategy]) -> None:
        self._strategies: list[ExtractionStrategy] = list(strategies)

    def execute(self, raw: str) -> ChainResult:
        """Run all strategies in order and return the first successful result.

        Raises:
            UpstreamStructureChangedError: When no strategy can handle the input,
                or when the strategy list is empty. The exception message includes
                diagnostic output from every attempted strategy.
        """
        if not self._strategies:
            raise UpstreamStructureChangedError("ProviderChain has no strategies registered.")

        probe_results: list[tuple[str, bool, str]] = []
        for strategy in self._strategies:
            name = strategy.fingerprint().source
            result = strategy.can_handle(raw)
            probe_results.append((name, result.can_handle, result.diagnostics))

            if not result.can_handle:
                continue

            df = strategy.extract(raw)
            return ChainResult(strategy_used=name, probe_results=probe_results, df=df)

        # All strategies rejected the input — build diagnostic summary and raise.
        diag_lines = [f"  [{name}] {'OK' if ok else 'FAIL'}: {msg}" for name, ok, msg in probe_results]
        diag_summary = "\n".join(diag_lines)
        raise UpstreamStructureChangedError(
            f"All {len(self._strategies)} strategies failed to handle the input.\nStrategy diagnostics:\n{diag_summary}"
        )
