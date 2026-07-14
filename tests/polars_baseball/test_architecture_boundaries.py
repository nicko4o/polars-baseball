from __future__ import annotations

import ast
from pathlib import Path

from polars_baseball._cache import generate_cache_key
from polars_baseball.apis.mlb._contracts import venues_cache_key, venues_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "polars_baseball"
MLB_API_ROOT = PACKAGE_ROOT / "apis" / "mlb"

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

    assert venues_cache_key(venue_ids) == expected_key
