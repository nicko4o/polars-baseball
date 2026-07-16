"""RED tests for Savant extraction strategies + ProviderChain integration."""

import polars as pl
import pytest

from polars_baseball.exceptions import UpstreamParseError, UpstreamStructureChangedError
from polars_baseball.parsers._strategy import ExtractionStrategy, ProviderChain

_SAVANT_CSV = (
    b"player_id,player_name,team,pos,oaa,season\n660271,Ohtani Shohei,LAA,OF,10,2023\n545361,Trout Mike,LAA,CF,8,2023\n"
)
_SAVANT_HTML = b"""<!DOCTYPE html>
<html><head><title>Statcast Outs Above Average Leaderboard</title></head>
<body>
<div class="leaderboard-container">
<table id="leaderboard_table">
<thead><tr>
<th>player_id</th><th>player_name</th><th>team</th><th>pos</th><th>oaa</th><th>season</th>
</tr></thead>
<tbody>
<tr>
<td>660271</td><td><a href="/player/660271">Ohtani, Shohei</a></td><td>LAA</td><td>OF</td><td>10</td><td>2023</td>
</tr>
<tr>
<td>545361</td><td><a href="/player/545361">Trout, Mike</a></td><td>LAA</td><td>CF</td><td>8</td><td>2023</td>
</tr>
</tbody>
</table>
</div>
</body></html>"""
_PLAIN_TEXT = b"this is just some random text without any structure"


# ---------------------------------------------------------------------------
# Import tests: strategies must exist
# ---------------------------------------------------------------------------


def test_savant_csv_strategy_is_importable() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantCSVStrategy

    strategy = SavantCSVStrategy()
    assert isinstance(strategy, ExtractionStrategy)


def test_savant_html_strategy_is_importable() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    strategy = SavantHTMLTableStrategy()
    assert isinstance(strategy, ExtractionStrategy)


# ---------------------------------------------------------------------------
# SavantCSVStrategy probing
# ---------------------------------------------------------------------------


def test_csv_strategy_accepts_csv() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantCSVStrategy

    strategy = SavantCSVStrategy()
    result = strategy.can_handle(_SAVANT_CSV.decode("utf-8"))
    assert result.can_handle is True


def test_csv_strategy_rejects_html() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantCSVStrategy

    strategy = SavantCSVStrategy()
    result = strategy.can_handle(_SAVANT_HTML.decode("utf-8"))
    assert result.can_handle is False


def test_csv_strategy_rejects_empty() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantCSVStrategy

    strategy = SavantCSVStrategy()
    result = strategy.can_handle("")
    assert result.can_handle is False


def test_csv_strategy_extracts_dataframe() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantCSVStrategy

    strategy = SavantCSVStrategy()
    df = strategy.extract(_SAVANT_CSV.decode("utf-8"))
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "player_id" in df.columns
    assert df["player_name"].to_list() == ["Ohtani Shohei", "Trout Mike"]


def test_csv_strategy_fingerprint_source() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantCSVStrategy

    fp = SavantCSVStrategy().fingerprint()
    assert "Savant" in fp.source
    assert "CSV" in fp.source


# ---------------------------------------------------------------------------
# SavantHTMLTableStrategy probing
# ---------------------------------------------------------------------------


def test_html_strategy_accepts_savant_html() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    strategy = SavantHTMLTableStrategy()
    result = strategy.can_handle(_SAVANT_HTML.decode("utf-8"))
    assert result.can_handle is True


def test_html_strategy_rejects_csv() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    strategy = SavantHTMLTableStrategy()
    result = strategy.can_handle(_SAVANT_CSV.decode("utf-8"))
    assert result.can_handle is False


def test_html_strategy_rejects_empty() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    strategy = SavantHTMLTableStrategy()
    result = strategy.can_handle("")
    assert result.can_handle is False


def test_html_strategy_rejects_plain_text() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    strategy = SavantHTMLTableStrategy()
    result = strategy.can_handle(_PLAIN_TEXT.decode("utf-8"))
    assert result.can_handle is False


def test_html_strategy_extracts_dataframe() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    strategy = SavantHTMLTableStrategy()
    df = strategy.extract(_SAVANT_HTML.decode("utf-8"))
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "player_id" in df.columns
    assert "oaa" in df.columns


def test_html_strategy_extracts_player_names() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    strategy = SavantHTMLTableStrategy()
    df = strategy.extract(_SAVANT_HTML.decode("utf-8"))
    names = df["player_name"].to_list()
    assert "Ohtani, Shohei" in names
    assert "Trout, Mike" in names


def test_html_strategy_raises_on_parser_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    import lxml.etree

    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    def broken_html_parser(_raw: str) -> None:
        raise ValueError("broken html parser")

    monkeypatch.setattr(lxml.etree, "HTML", broken_html_parser)
    strategy = SavantHTMLTableStrategy()

    with pytest.raises(UpstreamParseError, match="Savant HTML leaderboard parsing failed"):
        strategy.extract(_SAVANT_HTML.decode("utf-8"))


def test_html_strategy_fingerprint_source() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    fp = SavantHTMLTableStrategy().fingerprint()
    assert "Savant" in fp.source
    assert "HTML" in fp.source


# ---------------------------------------------------------------------------
# ProviderChain fallback
# ---------------------------------------------------------------------------


def test_chain_prefers_csv_when_both_match() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import (
        SavantCSVStrategy,
        SavantHTMLTableStrategy,
    )

    chain = ProviderChain([SavantCSVStrategy(), SavantHTMLTableStrategy()])
    result = chain.execute(_SAVANT_CSV.decode("utf-8"))
    assert result.strategy_used == "Savant-CSV"
    assert result.df.height == 2


def test_chain_falls_back_to_html_when_csv_rejects() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import (
        SavantCSVStrategy,
        SavantHTMLTableStrategy,
    )

    chain = ProviderChain([SavantCSVStrategy(), SavantHTMLTableStrategy()])
    result = chain.execute(_SAVANT_HTML.decode("utf-8"))
    assert result.strategy_used == "Savant-HTML-Table"
    assert result.df.height == 2


def test_chain_raises_when_all_strategies_fail() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import (
        SavantCSVStrategy,
        SavantHTMLTableStrategy,
    )

    chain = ProviderChain([SavantCSVStrategy(), SavantHTMLTableStrategy()])
    with pytest.raises(UpstreamStructureChangedError):
        chain.execute(_PLAIN_TEXT.decode("utf-8"))


def test_chain_probe_results_contain_both_strategies() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import (
        SavantCSVStrategy,
        SavantHTMLTableStrategy,
    )

    chain = ProviderChain([SavantCSVStrategy(), SavantHTMLTableStrategy()])
    result = chain.execute(_SAVANT_HTML.decode("utf-8"))
    names = [name for name, _, _ in result.probe_results]
    assert "Savant-CSV" in names
    assert "Savant-HTML-Table" in names


# ---------------------------------------------------------------------------
# Empty HTML table handling
# ---------------------------------------------------------------------------


def test_html_strategy_empty_table() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    html = "<html><body><table></table></body></html>"
    strategy = SavantHTMLTableStrategy()
    assert strategy.can_handle(html).can_handle is True
    df = strategy.extract(html)
    assert df.is_empty()


def test_html_strategy_no_table_in_html() -> None:
    from polars_baseball.parsers.savant_leaderboard_strategy import SavantHTMLTableStrategy

    html = "<html><body><p>No table here</p></body></html>"
    strategy = SavantHTMLTableStrategy()
    result = strategy.can_handle(html)
    assert result.can_handle is False


def test_savant_schema_overrides() -> None:
    from polars_baseball.parsers.savant_schema import SAVANT_SCHEMA_OVERRIDES

    assert "bat_speed" in SAVANT_SCHEMA_OVERRIDES
    assert SAVANT_SCHEMA_OVERRIDES["bat_speed"] == pl.Float64

    assert "swing_length" in SAVANT_SCHEMA_OVERRIDES
    assert SAVANT_SCHEMA_OVERRIDES["swing_length"] == pl.Float64

    assert "miss_distance" in SAVANT_SCHEMA_OVERRIDES
    assert SAVANT_SCHEMA_OVERRIDES["miss_distance"] == pl.Float64

    assert SAVANT_SCHEMA_OVERRIDES["game_pk"] == pl.Int64
    assert SAVANT_SCHEMA_OVERRIDES["pitcher"] == pl.Int64
