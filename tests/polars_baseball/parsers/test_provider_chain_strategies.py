"""RED tests for ProviderChain + ExtractionStrategy + StructureFingerprint."""

from __future__ import annotations

import polars as pl
import pytest

from polars_baseball.exceptions import UpstreamStructureChangedError
from polars_baseball.parsers._strategy import (
    ExtractionStrategy,
    ProbeResult,
    ProviderChain,
    StructureFingerprint,
)

# ---------------------------------------------------------------------------
# Fixtures: mock strategies
# ---------------------------------------------------------------------------


class _AlwaysOkStrategy:
    def can_handle(self, raw: str) -> ProbeResult:
        return ProbeResult(can_handle=True, diagnostics="always ok")

    def extract(self, raw: str) -> pl.DataFrame:
        return pl.DataFrame({"result": ["ok"]})

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source="always-ok", required_indicators=("should_never_matter",))


class _NeverOkStrategy:
    def can_handle(self, raw: str) -> ProbeResult:
        return ProbeResult(can_handle=False, diagnostics="never ok")

    def extract(self, raw: str) -> pl.DataFrame:
        raise RuntimeError("should not be called")

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source="never-ok", required_indicators=("will_not_exist",))


class _SometimesOkStrategy:
    """Succeeds only when raw contains a configurable keyword."""

    def __init__(self, keyword: str) -> None:
        self._keyword = keyword

    def can_handle(self, raw: str) -> ProbeResult:
        ok = self._keyword in raw
        return ProbeResult(
            can_handle=ok,
            diagnostics=f"keyword '{self._keyword}' {'found' if ok else 'missing'}",
        )

    def extract(self, raw: str) -> pl.DataFrame:
        return pl.DataFrame({"result": [f"parsed_{self._keyword}"]})

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source=f"sometimes-ok-{self._keyword}", required_indicators=(self._keyword,))


class _UnstableExtractStrategy:
    """can_handle succeeds but extract raises."""

    def can_handle(self, raw: str) -> ProbeResult:
        return ProbeResult(can_handle=True, diagnostics="can handle but will fail on extract")

    def extract(self, raw: str) -> pl.DataFrame:
        raise UpstreamStructureChangedError("simulated parse failure")

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source="unstable", required_indicators=("_",))


# ---------------------------------------------------------------------------
# StructureFingerprint
# ---------------------------------------------------------------------------


class TestStructureFingerprint:
    def test_diff_returns_empty_when_all_indicators_present(self) -> None:
        fp = StructureFingerprint(source="test", required_indicators=("abc", "def"))
        diff = fp.diff("abc and def are both here")
        assert diff == ""

    def test_diff_reports_missing_indicators(self) -> None:
        fp = StructureFingerprint(source="test", required_indicators=("abc", "ghi"))
        diff = fp.diff("abc and def are both here")
        assert "ghi" in diff

    def test_diff_empty_indicators(self) -> None:
        fp = StructureFingerprint(source="test", required_indicators=())
        diff = fp.diff("any content at all")
        assert diff == ""

    def test_diff_multiple_missing(self) -> None:
        fp = StructureFingerprint(source="test", required_indicators=("abc", "def", "ghi"))
        diff = fp.diff("nothing matches here")
        assert "abc" in diff
        assert "def" in diff
        assert "ghi" in diff


# ---------------------------------------------------------------------------
# ProbeResult
# ---------------------------------------------------------------------------


class TestProbeResult:
    def test_default_diagnostics_is_empty_string(self) -> None:
        r = ProbeResult(can_handle=True)
        assert r.diagnostics == ""

    def test_repr_contains_status(self) -> None:
        r = ProbeResult(can_handle=False, diagnostics="failed")
        assert "failed" in repr(r)


# ---------------------------------------------------------------------------
# ProviderChain
# ---------------------------------------------------------------------------


class TestProviderChainSingleStrategy:
    def test_single_strategy_can_handle(self) -> None:
        chain = ProviderChain([_AlwaysOkStrategy()])
        result = chain.execute("anything")
        assert result.strategy_used == "always-ok"
        assert isinstance(result.df, pl.DataFrame)
        assert result.df["result"].to_list() == ["ok"]

    def test_single_strategy_cannot_handle(self) -> None:
        """When the single strategy rejects input, execute() must raise."""
        chain = ProviderChain([_NeverOkStrategy()])
        with pytest.raises(UpstreamStructureChangedError):
            chain.execute("anything")

    def test_empty_strategies_list(self) -> None:
        """An empty strategy list must raise immediately."""
        chain = ProviderChain([])
        with pytest.raises(UpstreamStructureChangedError):
            chain.execute("anything")

    def test_extract_error_bubbles_up(self) -> None:
        """If can_handle passes but extract fails, the error should propagate."""
        chain = ProviderChain([_UnstableExtractStrategy()])
        with pytest.raises(UpstreamStructureChangedError, match="simulated parse failure"):
            chain.execute("anything")


class TestProviderChainFallback:
    def test_fallback_on_first_strategy_unable_to_handle(self) -> None:
        chain = ProviderChain([_NeverOkStrategy(), _AlwaysOkStrategy()])
        result = chain.execute("anything")
        assert result.strategy_used == "always-ok"
        assert result.df is not None

    def test_uses_first_matching_strategy(self) -> None:
        chain = ProviderChain([_SometimesOkStrategy("speed"), _SometimesOkStrategy("angle")])
        result = chain.execute("some launch speed data")
        assert result.strategy_used == "sometimes-ok-speed"
        assert result.df is not None
        assert result.df["result"].to_list() == ["parsed_speed"]

    def test_fallback_to_second_when_first_missing_keyword(self) -> None:
        chain = ProviderChain([_SometimesOkStrategy("speed"), _SometimesOkStrategy("angle")])
        result = chain.execute("launch angle only here")
        assert result.strategy_used == "sometimes-ok-angle"
        assert result.df is not None
        assert result.df["result"].to_list() == ["parsed_angle"]

    def test_all_strategies_fail(self) -> None:
        """When every strategy rejects the input, execute() must raise with diagnostics."""
        chain = ProviderChain([_SometimesOkStrategy("speed"), _SometimesOkStrategy("angle")])
        with pytest.raises(UpstreamStructureChangedError):
            chain.execute("has neither keyword")


class TestProviderChainDiagnostics:
    def test_probe_results_included_in_result(self) -> None:
        chain = ProviderChain([_NeverOkStrategy(), _AlwaysOkStrategy()])
        result = chain.execute("anything")
        assert len(result.probe_results) == 2
        assert result.probe_results[0] == ("never-ok", False, "never ok")
        assert result.probe_results[1] == ("always-ok", True, "always ok")

    def test_probe_results_when_all_fail(self) -> None:
        """Diagnostics from all failed strategies are embedded in the exception message."""
        chain = ProviderChain([_NeverOkStrategy(), _NeverOkStrategy()])
        with pytest.raises(UpstreamStructureChangedError) as exc_info:
            chain.execute("anything")
        # Both strategy names must appear in the exception message.
        assert "never-ok" in str(exc_info.value)


# ---------------------------------------------------------------------------
# ExtractionStrategy protocol adherence
# ---------------------------------------------------------------------------


class TestExtractionStrategyProtocol:
    def test_always_ok_is_valid_strategy(self) -> None:
        s: ExtractionStrategy = _AlwaysOkStrategy()
        assert s.can_handle("x").can_handle is True
        assert s.extract("x").height == 1
        assert s.fingerprint().source == "always-ok"

    def test_never_ok_is_valid_strategy(self) -> None:
        s: ExtractionStrategy = _NeverOkStrategy()
        assert s.can_handle("x").can_handle is False
        assert s.fingerprint().source == "never-ok"

    def test_sometimes_ok_is_valid_strategy(self) -> None:
        s: ExtractionStrategy = _SometimesOkStrategy("test")
        assert s.can_handle("test").can_handle is True
        assert s.can_handle("other").can_handle is False


# ---------------------------------------------------------------------------
# BRef standard strategy wrapper (integration test with existing parser)
# ---------------------------------------------------------------------------


class TestBRefStandardStrategy:
    def test_wrapper_produces_valid_strategy(self) -> None:
        from polars_baseball.parsers.bref import BRefHTMLParser
        from polars_baseball.parsers.bref_standard_strategy import BRefStandardStrategy

        strategy = BRefStandardStrategy(BRefHTMLParser())
        assert isinstance(strategy, ExtractionStrategy)

        # A minimal BRef-like HTML snippet
        html = """
        <html><body>
        <table>
            <tr><th>Name</th><th>AB</th><th>BA</th></tr>
            <tbody>
            <tr><td>Player A</td><td>100</td><td>.300</td></tr>
            </tbody>
        </table>
        </body></html>
        """
        result = strategy.can_handle(html)
        assert result.can_handle is True

        df = strategy.extract(html)
        assert isinstance(df, pl.DataFrame)
        assert df.height >= 1

    def test_fingerprint_reports_source(self) -> None:
        from polars_baseball.parsers.bref import BRefHTMLParser
        from polars_baseball.parsers.bref_standard_strategy import BRefStandardStrategy

        strategy = BRefStandardStrategy(BRefHTMLParser())
        fp = strategy.fingerprint()
        assert "BRef" in fp.source


# ------------------------------------------------- --------------------------
# Fangraphs strategy wrapper
# ---------------------------------------------------------------------------


class TestFangraphsNextDataStrategy:
    def test_wrapper_produces_valid_strategy(self) -> None:
        from polars_baseball.parsers.fangraphs_next_data_strategy import FangraphsNextDataStrategy

        strategy = FangraphsNextDataStrategy()
        assert isinstance(strategy, ExtractionStrategy)

        # Minimal Fangraphs-like HTML with NEXT_DATA
        import json

        next_data = {
            "props": {
                "pageProps": {
                    "dehydratedState": {
                        "queries": [
                            {
                                "queryKey": ["leaders/major-league/data", {}],
                                "state": {"data": {"data": [{"Name": "P1", "WAR": 5.0}]}},
                            }
                        ]
                    }
                }
            }
        }
        html = f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script></html>'
        result = strategy.can_handle(html)
        assert result.can_handle is True

    def test_rejects_non_next_data_html(self) -> None:
        from polars_baseball.parsers.fangraphs_next_data_strategy import FangraphsNextDataStrategy

        strategy = FangraphsNextDataStrategy()
        html = "<html><body><p>Not a Fangraphs page</p></body></html>"
        result = strategy.can_handle(html)
        assert result.can_handle is False


# ---------------------------------------------------------------------------
# BRef game log strategy wrapper
# ---------------------------------------------------------------------------


class TestBRefGameLogStrategy:
    def test_wrapper_produces_valid_strategy(self) -> None:
        from polars_baseball.parsers.bref import BRefGameLogParser
        from polars_baseball.parsers.bref_standard_strategy import BRefGameLogStrategy

        strategy = BRefGameLogStrategy(BRefGameLogParser("batting"))
        assert isinstance(strategy, ExtractionStrategy)

        html = """
        <html><body>
        <table id="players_standard_batting">
            <thead><tr><th>Game</th><th>AB</th></tr></thead>
            <tbody><tr><td>1</td><td>4</td></tr></tbody>
        </table>
        </body></html>
        """
        assert strategy.can_handle(html).can_handle is True
        df = strategy.extract(html)
        assert isinstance(df, pl.DataFrame)


# ---------------------------------------------------------------------------
# BRef CSV export strategy
# ---------------------------------------------------------------------------


class TestBRefCSVExportStrategy:
    def test_csv_table_detected(self) -> None:
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy

        strategy = BRefCSVExportStrategy()
        html = '<table id="csv_players_standard_batting"><tr><td>a,b</td></tr></table>'
        result = strategy.can_handle(html)
        assert result.can_handle is True

    def test_rejects_html_without_csv(self) -> None:
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy

        strategy = BRefCSVExportStrategy()
        html = "<html><body><p>No CSV here</p></body></html>"
        result = strategy.can_handle(html)
        assert result.can_handle is False

    def test_extract_from_csv_table(self) -> None:
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy

        strategy = BRefCSVExportStrategy()
        html = """
        <html><body>
        <table id="csv_players_standard_batting">
            <tr><td>Name</td><td>G</td><td>AB</td><td>BA</td></tr>
            <tr><td>Mike Trout</td><td>140</td><td>500</td><td>.300</td></tr>
            <tr><td>Shohei Ohtani</td><td>150</td><td>550</td><td>.280</td></tr>
        </table>
        </body></html>
        """
        assert strategy.can_handle(html).can_handle is True
        df = strategy.extract(html)
        assert df.height == 2
        assert "Name" in df.columns
        assert "G" in df.columns
        assert df["Name"].to_list() == ["Mike Trout", "Shohei Ohtani"]

    def test_extract_from_csv_div(self) -> None:
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy

        strategy = BRefCSVExportStrategy()
        html = (
            "<html><body>"
            '<div class="csv">Name,G,AB,BA\n'
            "Mike Trout,140,500,.300\n"
            "Shohei Ohtani,150,550,.280</div>"
            "</body></html>"
        )
        assert strategy.can_handle(html).can_handle is True
        df = strategy.extract(html)
        assert df.height == 2
        assert df["Name"].to_list() == ["Mike Trout", "Shohei Ohtani"]

    def test_extract_empty_html(self) -> None:
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy

        strategy = BRefCSVExportStrategy()
        df = strategy.extract("<html></html>")
        assert df.is_empty()

    def test_fingerprint_source(self) -> None:
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy

        strategy = BRefCSVExportStrategy()
        fp = strategy.fingerprint()
        assert "CSV" in fp.source
        assert "csv_" in fp.required_indicators


# ---------------------------------------------------------------------------
# Fallback integration: ProviderChain with BRefCSVExport + BRefStandardStrategy
# ---------------------------------------------------------------------------


class TestProviderChainBRefFallback:
    """Verifies graceful degradation from CSV export → DOM parsing."""

    def test_csv_succeeds_dom_not_touched(self) -> None:
        """When CSV export is present, DOM strategy is never called."""
        from polars_baseball.parsers.bref import BRefHTMLParser
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy, BRefStandardStrategy

        dom = BRefStandardStrategy(BRefHTMLParser())

        call_count: int = 0
        original_extract = dom.extract

        def tracking_extract(raw: str) -> pl.DataFrame:
            nonlocal call_count
            call_count += 1
            return original_extract(raw)

        dom.extract = tracking_extract  # type: ignore[method-assign]

        chain = ProviderChain([BRefCSVExportStrategy(), dom])

        # HTML with CSV table — DOM should NOT be called
        html = """
        <html><body>
        <table id="csv_players_standard_batting">
            <tr><td>Name,G,AB</td></tr>
            <tr><td>Player X,100,400</td></tr>
        </table>
        </body></html>
        """
        result = chain.execute(html)
        assert result.strategy_used == "BRef-CSV-Export"
        assert result.df is not None
        assert result.df.height == 1
        assert call_count == 0, "DOM strategy was called when CSV should have sufficed"

    def test_dom_fallback_when_csv_missing(self) -> None:
        """When no CSV export table exists, DOM parsing is used as fallback."""
        from polars_baseball.parsers.bref import BRefHTMLParser
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy, BRefStandardStrategy

        chain = ProviderChain([BRefCSVExportStrategy(), BRefStandardStrategy(BRefHTMLParser())])

        html = """
        <html><body>
        <table>
            <tr><th>Name</th><th>G</th><th>AB</th></tr>
            <tbody>
            <tr><td>Player A</td><td>100</td><td>400</td></tr>
            </tbody>
        </table>
        </body></html>
        """
        result = chain.execute(html)
        assert result.strategy_used == "BRef-Standard-Table"
        assert result.df is not None
        assert result.df.height >= 1

    def test_dom_fallback_when_no_csv_at_all(self) -> None:
        """Standard BRef page with no CSV export at all falls back to DOM."""
        from polars_baseball.parsers.bref import BRefHTMLParser
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy, BRefStandardStrategy

        chain = ProviderChain([BRefCSVExportStrategy(), BRefStandardStrategy(BRefHTMLParser())])

        html = """
        <html><body>
        <table>
            <tr><th>Name</th><th>AB</th></tr>
            <tbody>
            <tr><td>Fallback Player</td><td>200</td></tr>
            </tbody>
        </table>
        </body></html>
        """
        result = chain.execute(html)
        assert result.strategy_used == "BRef-Standard-Table"
        assert result.df is not None
        assert result.df.height >= 1

    def test_probe_results_contain_csv_failure_then_dom_success(self) -> None:
        """Diagnostics show CSV probe result and DOM probe result."""
        from polars_baseball.parsers.bref import BRefHTMLParser
        from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy, BRefStandardStrategy

        chain = ProviderChain([BRefCSVExportStrategy(), BRefStandardStrategy(BRefHTMLParser())])

        html = """
        <html><body>
        <table>
            <tr><th>G</th></tr>
            <tbody><tr><td>1</td></tr></tbody>
        </table>
        </body></html>
        """
        result = chain.execute(html)
        assert result.strategy_used == "BRef-Standard-Table"
        assert len(result.probe_results) == 2
        # CSV probe reports false
        assert result.probe_results[0][0] == "BRef-CSV-Export"
        assert result.probe_results[0][1] is False
        # DOM probe reports true
        assert result.probe_results[1][0] == "BRef-Standard-Table"
        assert result.probe_results[1][1] is True
