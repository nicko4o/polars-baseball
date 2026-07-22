"""Tests for ProviderChain fail-fast behavior.

Verifies that all-strategy-failure raises UpstreamStructureChangedError
with diagnostics, rather than silently returning df=None.
"""

import polars as pl
import pytest

from polars_baseball.exceptions import UpstreamStructureChangedError
from polars_baseball.parsers._strategy import (
    ChainResult,
    ProbeResult,
    ProviderChain,
    StructureFingerprint,
)

# ── Fixtures ──────────────────────────────────────────────────────────


class _AlwaysHandleStrategy:
    """Stub strategy that always claims it can handle the input."""

    def can_handle(self, raw: str) -> ProbeResult:
        return ProbeResult(can_handle=True, diagnostics="always yes")

    def extract(self, raw: str) -> pl.DataFrame:
        return pl.DataFrame({"col": [1]})

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source="AlwaysHandle", required_indicators=())


class _NeverHandleStrategy:
    """Stub strategy that always rejects the input."""

    def __init__(self, name: str = "NeverHandle") -> None:
        self._name = name

    def can_handle(self, raw: str) -> ProbeResult:
        return ProbeResult(can_handle=False, diagnostics=f"[{self._name}] rejected")

    def extract(self, raw: str) -> pl.DataFrame:  # pragma: no cover
        raise AssertionError("extract() must not be called when can_handle is False")

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source=self._name, required_indicators=("MISSING_INDICATOR",))


# ── Empty chain ───────────────────────────────────────────────────────


def test_empty_chain_raises() -> None:
    """An empty ProviderChain must raise, not silently succeed."""
    chain = ProviderChain([])
    with pytest.raises(UpstreamStructureChangedError):
        chain.execute("any content")


# ── All strategies fail ───────────────────────────────────────────────


def test_all_strategies_fail_raises_with_diagnostics() -> None:
    """When every strategy rejects the input, execute() must raise."""
    chain = ProviderChain([_NeverHandleStrategy("S1"), _NeverHandleStrategy("S2")])
    with pytest.raises(UpstreamStructureChangedError, match="S1"):
        chain.execute("garbage content")


def test_exception_message_contains_all_strategy_names() -> None:
    """Diagnostics in the raised exception must reference every tried strategy."""
    chain = ProviderChain([_NeverHandleStrategy("Alpha"), _NeverHandleStrategy("Beta")])
    with pytest.raises(UpstreamStructureChangedError) as exc_info:
        chain.execute("no match")

    msg = str(exc_info.value)
    assert "Alpha" in msg
    assert "Beta" in msg


# ── Successful extraction ─────────────────────────────────────────────


def test_first_matching_strategy_is_used() -> None:
    """execute() returns the DataFrame from the first matching strategy."""
    chain = ProviderChain([_NeverHandleStrategy(), _AlwaysHandleStrategy()])
    result = chain.execute("any content")
    assert isinstance(result, ChainResult)
    assert result.df is not None
    assert result.df.height == 1
    assert result.strategy_used == "AlwaysHandle"


def test_probe_results_recorded_for_all_tried_strategies() -> None:
    """probe_results must be populated for every strategy that was evaluated."""
    chain = ProviderChain([_NeverHandleStrategy("S1"), _AlwaysHandleStrategy()])
    result = chain.execute("content")
    names = [name for name, _, _ in result.probe_results]
    assert "S1" in names
    assert "AlwaysHandle" in names


def test_first_strategy_wins_if_both_can_handle() -> None:
    """When multiple strategies match, the first one takes precedence."""

    class _SecondStrategy:
        def can_handle(self, raw: str) -> ProbeResult:
            return ProbeResult(can_handle=True, diagnostics="second")

        def extract(self, raw: str) -> pl.DataFrame:
            return pl.DataFrame({"col": [99]})

        def fingerprint(self) -> StructureFingerprint:
            return StructureFingerprint(source="Second", required_indicators=())

    chain = ProviderChain([_AlwaysHandleStrategy(), _SecondStrategy()])
    result = chain.execute("content")
    assert result.strategy_used == "AlwaysHandle"
    assert result.df is not None
    assert result.df["col"][0] == 1


class _FailingExtractStrategy:
    def can_handle(self, raw: str) -> ProbeResult:
        return ProbeResult(can_handle=True, diagnostics="Matches test structure")

    def extract(self, raw: str) -> pl.DataFrame:
        raise ValueError("Extraction syntax error")

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source="FailingStrategy", required_indicators=())


def test_extract_error_retains_diagnostics() -> None:
    chain = ProviderChain([_FailingExtractStrategy()])
    with pytest.raises(UpstreamStructureChangedError) as exc_info:
        chain.execute("{}")
    assert "FailingStrategy" in str(exc_info.value)
    assert "Matches test structure" in str(exc_info.value)
