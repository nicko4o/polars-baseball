from __future__ import annotations

import ast
from pathlib import Path

from polars_baseball._cache import CacheCallArgs, generate_cache_key, global_cache
from polars_baseball.apis.mlb._contracts import venues_cache_key, venues_url
from polars_baseball.context import BaseballContext

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "polars_baseball"
MLB_API_ROOT = PACKAGE_ROOT / "apis" / "mlb"
RETROSHEET_API = PACKAGE_ROOT / "apis" / "retrosheet.py"

MLB_SHARED_ENDPOINT_CONSTANTS = {
    "_BOXSCORE_URL_TEMPLATE",
    "_DIVISIONS_URL",
    "_LEAGUES_URL",
    "_LINESCORE_URL_TEMPLATE",
    "_PEOPLE_AWARDS_URL_TEMPLATE",
    "_PEOPLE_STATS_URL_TEMPLATE",
    "_PEOPLE_URL",
    "_ROSTER_URL_TEMPLATE",
    "_SCHEDULE_URL",
    "_STAT_LEADERS_URL",
    "_TEAM_STATS_URL_TEMPLATE",
    "_TEAMS_URL",
}

ALLOWED_MLB_CONTRACT_MODULE = MLB_API_ROOT / "_contracts.py"


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.name != "__init__.py")


def test_mlb_endpoint_constants_have_single_contract_module() -> None:
    offenders: list[str] = []
    for path in _python_files(MLB_API_ROOT):
        if path == ALLOWED_MLB_CONTRACT_MODULE:
            continue
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.AnnAssign | ast.Assign):
                continue
            targets = [node.target] if isinstance(node, ast.AnnAssign) else list(node.targets)
            names = [target.id for target in targets if isinstance(target, ast.Name)]
            duplicate_names = sorted(MLB_SHARED_ENDPOINT_CONSTANTS.intersection(names))
            if duplicate_names:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: {', '.join(duplicate_names)}")

    assert offenders == []


def test_cache_module_does_not_depend_on_context_module() -> None:
    path = PACKAGE_ROOT / "_cache.py"
    tree = ast.parse(path.read_text())
    forbidden_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "polars_baseball.context":
            forbidden_imports.append(f"line {node.lineno}: from {node.module} import ...")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "polars_baseball.context":
                    forbidden_imports.append(f"line {node.lineno}: import {alias.name}")

    assert forbidden_imports == []


def test_venue_list_cache_key_matches_fetch_contract() -> None:
    venue_ids = [10, 20]
    expected_key = generate_cache_key(venues_url(), {"venueIds": "10,20"})
    call = CacheCallArgs(
        context=BaseballContext(cache=global_cache), arguments={"venue_ids": venue_ids}, force_update=False
    )

    assert venues_cache_key(call) == expected_key


def test_mlb_api_layer_does_not_own_parser_schema_casting() -> None:
    offenders: list[str] = []
    for path in _python_files(MLB_API_ROOT):
        if path == ALLOWED_MLB_CONTRACT_MODULE:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "polars_baseball._schema_utils":
                imported_names = {alias.name for alias in node.names}
                if "validate_and_cast_schema" in imported_names:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} imports schema casting")
            if isinstance(node, ast.FunctionDef) and node.name.startswith("_parse_mlb"):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} defines {node.name}")

    assert offenders == []


def test_retrosheet_api_layer_does_not_own_csv_or_json_parsing() -> None:
    tree = ast.parse(RETROSHEET_API.read_text())
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"io", "json"}:
                    offenders.append(f"line {node.lineno}: import {alias.name}")
        if isinstance(node, ast.ImportFrom) and node.module == "polars_baseball._schemas.retrosheet":
            offenders.append(f"line {node.lineno}: imports retrosheet schemas")
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"read_csv", "loads"}:
            offenders.append(f"line {node.lineno}: calls {func.attr}")

    assert offenders == []
