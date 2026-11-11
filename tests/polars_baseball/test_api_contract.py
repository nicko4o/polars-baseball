import inspect
import re
from pathlib import Path

import pytest

import polars_baseball as pb

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROVIDER_DOCS_MAP = {
    "savant": "docs/reference/statcast.md",
    "mlb": "docs/reference/mlb_api.md",
    "fangraphs": "docs/reference/fangraphs.md",
    "bref": "docs/reference/bref.md",
    "retrosheet": "docs/reference/retrosheet.md",
    "lahman": "docs/reference/lahman.md",
    "lookup": "docs/reference/lookups.md",
}

ROOT_PUBLIC_API = {
    "BaseballClient",
    "KeyType",
    "Position",
    "bref",
    "fangraphs",
    "lahman",
    "lookup",
    "mlb",
    "retrosheet",
    "savant",
}

IMPLEMENTATION_NAMESPACE_LEAKS = {
    "apis",
    "client",
    "context",
    "enums",
    "exceptions",
    "gateways",
    "logging",
    "parsers",
}


def test_public_api_symbols_exist() -> None:
    public_symbols = {name for name in dir(pb) if not name.startswith("_")}
    missing = ROOT_PUBLIC_API - public_symbols
    assert not missing, f"Missing public symbols: {missing}"


def test_root_all_is_stable_public_api() -> None:
    assert set(pb.__all__) == ROOT_PUBLIC_API | {"__version__"}


def test_root_namespace_hides_implementation_packages() -> None:
    public_symbols = {name for name in dir(pb) if not name.startswith("_")}
    leaks = public_symbols & IMPLEMENTATION_NAMESPACE_LEAKS
    assert not leaks, f"Implementation namespaces leaked at package root: {leaks}"


def test_root_namespace_has_no_unlisted_user_facing_symbols() -> None:
    public_symbols = {name for name in dir(pb) if not name.startswith("_")}
    extra_ok = public_symbols - ROOT_PUBLIC_API
    missing = ROOT_PUBLIC_API - public_symbols
    assert not missing, f"Missing public symbols: {missing}"
    assert not extra_ok, f"Unexpected symbols in public namespace: {extra_ok}"


def test_client_subclients_methods_are_async() -> None:
    client = pb.BaseballClient()
    assert inspect.iscoroutinefunction(client.savant.statcast)
    assert inspect.iscoroutinefunction(client.savant.scan_statcast)
    assert inspect.iscoroutinefunction(client.savant.sync_statcast)
    assert inspect.iscoroutinefunction(client.savant.park_factors)
    assert inspect.iscoroutinefunction(client.savant.gamefeed_pitch_data)
    assert inspect.iscoroutinefunction(client.savant.composite_percentile_ranks)
    assert inspect.iscoroutinefunction(client.savant.player_percentile_profile)

    assert inspect.iscoroutinefunction(client.mlb.schedule)
    assert inspect.iscoroutinefunction(client.mlb.game_boxscore)
    assert inspect.iscoroutinefunction(client.mlb.film_room_search)
    assert inspect.iscoroutinefunction(client.mlb.standings)

    assert inspect.iscoroutinefunction(client.fangraphs.batting)
    assert inspect.iscoroutinefunction(client.fangraphs.pitching)

    assert inspect.iscoroutinefunction(client.bref.bwar_bat)
    assert inspect.iscoroutinefunction(client.bref.game_logs)
    assert inspect.iscoroutinefunction(client.bref.splits)

    assert inspect.iscoroutinefunction(client.retrosheet.events)
    assert inspect.iscoroutinefunction(client.retrosheet.rosters)

    assert inspect.iscoroutinefunction(client.lahman.batting)
    assert inspect.iscoroutinefunction(client.lahman.pitching)

    assert inspect.iscoroutinefunction(client.lookup.playerid_lookup)
    assert inspect.iscoroutinefunction(client.lookup.playerid_reverse_lookup)
    assert inspect.iscoroutinefunction(client.lookup.chadwick_register)


@pytest.mark.parametrize(
    ("module", "func_name"),
    [
        (pb.savant, "statcast"),
        (pb.mlb, "schedule"),
        (pb.bref, "bwar_bat"),
        (pb.fangraphs, "batting"),
        (pb.retrosheet, "events"),
        (pb.lahman, "batting"),
        (pb.lookup, "playerid_lookup"),
    ],
)
def test_removed_toplevel_functions_raise_attribute_error(module: object, func_name: str) -> None:
    with pytest.raises(AttributeError):
        getattr(module, func_name)


def test_root_public_api_has_docstrings() -> None:
    missing_docstrings = [
        name
        for name in ROOT_PUBLIC_API
        if (inspect.isfunction(getattr(pb, name)) or inspect.isclass(getattr(pb, name)))
        and not inspect.getdoc(getattr(pb, name))
    ]

    assert not missing_docstrings, f"Root public API missing docstrings: {missing_docstrings}"


def test_root_public_api_docstrings_do_not_use_numpy_sections() -> None:
    numpy_style_docstrings = []
    for name in ROOT_PUBLIC_API:
        doc = inspect.getdoc(getattr(pb, name))
        if doc is not None and "----------" in doc:
            numpy_style_docstrings.append(name)

    assert not numpy_style_docstrings, f"Root public API docstrings use NumPy-style sections: {numpy_style_docstrings}"


def test_all_client_subclient_methods_are_documented() -> None:
    client = pb.BaseballClient()
    missing_docs: list[str] = []
    for subclient_name, doc_rel in PROVIDER_DOCS_MAP.items():
        doc_path = _PROJECT_ROOT / doc_rel
        doc_text = doc_path.read_text(encoding="utf-8")
        subclient = getattr(client, subclient_name)
        public_methods = {m for m in dir(subclient) if not m.startswith("_") and callable(getattr(subclient, m))}
        for method in public_methods:
            if method not in doc_text:
                missing_docs.append(f"{subclient_name}.{method} not documented in {doc_rel}")

    assert not missing_docs, "Client methods missing from reference docs: " + ", ".join(missing_docs)


def test_reference_docs_do_not_document_ghost_client_methods() -> None:
    client = pb.BaseballClient()
    ghost_methods: list[str] = []
    func_pattern = re.compile(r"`(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)\(")

    COMMON_EXCLUSIONS = {
        "print",
        "main",
        "select",
        "head",
        "filter",
        "group_by",
        "agg",
        "sort",
        "alias",
        "len",
        "col",
        "atan2",
        "pi",
        "run",
        "with_file_cache",
        "close",
        "with_null_cache",
        "show",
        "items",
        "keys",
        "values",
        "read_csv",
        "cast",
        "lit",
        "str",
        "int",
        "float",
        "bool",
        "dict",
        "list",
        "tuple",
        "set",
        "BaseballClient",
        "BaseballContext",
    }

    for subclient_name, doc_rel in PROVIDER_DOCS_MAP.items():
        doc_path = _PROJECT_ROOT / doc_rel
        doc_text = doc_path.read_text(encoding="utf-8")
        subclient = getattr(client, subclient_name)
        subclient_methods = {m for m in dir(subclient) if not m.startswith("_") and callable(getattr(subclient, m))}
        submodule = getattr(pb, subclient_name)
        submodule_callables = {m for m in dir(submodule) if not m.startswith("_") and callable(getattr(submodule, m))}
        allowed = subclient_methods | submodule_callables | COMMON_EXCLUSIONS

        # Extract function names documented in inline code: `func(...)` or `sub.func(...)`
        matches = func_pattern.findall(doc_text)
        for func_name in set(matches):
            if func_name.startswith("_") or func_name in allowed:
                continue
            # Check if this method exists on any client subclient
            exists_anywhere = any(hasattr(getattr(client, other_sub), func_name) for other_sub in PROVIDER_DOCS_MAP)
            if exists_anywhere:
                ghost_methods.append(
                    f"{doc_rel}: `{func_name}(...)` is documented in {subclient_name} doc, but belongs to another subclient"
                )
            else:
                ghost_methods.append(f"{doc_rel}: `{func_name}(...)` does not exist on {subclient_name}")

    assert not ghost_methods, "Ghost/misplaced methods documented: " + ", ".join(ghost_methods)
