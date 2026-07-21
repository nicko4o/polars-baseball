import tomllib
from pathlib import Path

import polars_baseball

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_manifest_includes_runtime_json_data() -> None:
    manifest_text = (_PROJECT_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "include polars_baseball/data/*.json" in manifest_text
    assert "prune scratch" in manifest_text


def test_package_discovery_excludes_non_package_scratch_tree() -> None:
    pyproject_text = (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'include = ["polars_baseball*"]' in pyproject_text
    assert '"scratch*"' in pyproject_text


def test_runtime_dependencies_include_imported_backports() -> None:
    pyproject_text = (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"typing_extensions>=4.0.0"' in pyproject_text


def test_version_in_pyproject_matches_package_init() -> None:
    pyproject_path = _PROJECT_ROOT / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    bump_version = config["tool"]["bumpversion"]["current_version"]
    assert polars_baseball.__version__ == bump_version, (
        f"polars_baseball.__version__ ({polars_baseball.__version__}) "
        f"does not match pyproject.toml bumpversion ({bump_version})"
    )
