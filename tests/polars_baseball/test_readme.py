import ast
import importlib
import inspect
import re
from pathlib import Path

import polars_baseball as pb

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PYTHON_FENCE_RE = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
_INLINE_SIGNATURE_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)\((.*?)\)\s*->")
_PARAMETER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:")
_DOCUMENTED_ROOT_API_EXEMPTIONS = {
    "ArsenalType",
    "KeyType",
}
_DOCUMENTED_MODULES = (
    "polars_baseball.apis.bref",
    "polars_baseball.apis.fangraphs",
    "polars_baseball.apis.lahman",
    "polars_baseball.apis.playerid",
    "polars_baseball.apis.retrosheet",
    "polars_baseball.apis.savant_fielding_running",
    "polars_baseball.apis.savant_gamefeed",
    "polars_baseball.apis.savant_leaderboards",
    "polars_baseball.apis.teamid",
)


def _markdown_files() -> list[Path]:
    docs_files = sorted((_PROJECT_ROOT / "docs").rglob("*.md"))
    return [_PROJECT_ROOT / "README.md", _PROJECT_ROOT / "README.zh-TW.md", *docs_files]


def _python_examples(path: Path) -> list[str]:
    return _PYTHON_FENCE_RE.findall(path.read_text(encoding="utf-8"))


def _documented_symbol(name: str) -> object | None:
    if hasattr(pb, name):
        return getattr(pb, name)
    for module_name in _DOCUMENTED_MODULES:
        module = importlib.import_module(module_name)
        if hasattr(module, name):
            return getattr(module, name)
    return None


def test_readme_python_examples_are_syntactically_valid() -> None:
    examples = _python_examples(_PROJECT_ROOT / "README.md")

    assert examples
    for example in examples:
        ast.parse(example)


def test_markdown_python_examples_are_syntactically_valid() -> None:
    for path in _markdown_files():
        for example in _python_examples(path):
            ast.parse(example)


def test_markdown_polars_baseball_imports_resolve() -> None:
    failures: list[str] = []
    for path in _markdown_files():
        for example in _python_examples(path):
            tree = ast.parse(example)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.module is None:
                    continue
                if not node.module.startswith("polars_baseball"):
                    continue
                try:
                    module = importlib.import_module(node.module)
                except ModuleNotFoundError:
                    failures.append(f"{path.relative_to(_PROJECT_ROOT)}: {node.module}")
                    continue
                for alias in node.names:
                    if alias.name != "*" and not hasattr(module, alias.name):
                        failures.append(f"{path.relative_to(_PROJECT_ROOT)}: {node.module}.{alias.name}")

    assert not failures, "Broken documented imports: " + ", ".join(failures)


def test_markdown_package_alias_attributes_resolve() -> None:
    failures: list[str] = []
    for path in _markdown_files():
        for example in _python_examples(path):
            tree = ast.parse(example)
            aliases = {
                alias.asname or alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
                if alias.name == "polars_baseball"
            }
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
                    continue
                if node.value.id in aliases and not hasattr(pb, node.attr):
                    failures.append(f"{path.relative_to(_PROJECT_ROOT)}: {node.value.id}.{node.attr}")

    assert not failures, "Broken documented package attributes: " + ", ".join(failures)


def test_markdown_inline_signatures_match_importable_symbols() -> None:
    failures: list[str] = []
    for path in _markdown_files():
        text = path.read_text(encoding="utf-8")
        for match in _INLINE_SIGNATURE_RE.finditer(text):
            name = match.group(1)
            symbol = _documented_symbol(name)
            if symbol is None:
                failures.append(f"{path.relative_to(_PROJECT_ROOT)}: {name} is not importable")
                continue
            assert callable(symbol)
            documented_params = set(_PARAMETER_RE.findall(match.group(2)))
            actual_params = set(inspect.signature(symbol).parameters)
            unsupported = sorted(documented_params - actual_params)
            if unsupported:
                failures.append(f"{path.relative_to(_PROJECT_ROOT)}: {name} unsupported params {unsupported}")

    assert not failures, "Broken documented inline signatures: " + ", ".join(failures)


def test_root_public_api_is_documented_in_markdown() -> None:
    markdown_text = "\n".join(path.read_text(encoding="utf-8") for path in _markdown_files())
    undocumented = sorted(
        name for name in pb.__all__ if name not in _DOCUMENTED_ROOT_API_EXEMPTIONS and name not in markdown_text
    )

    assert not undocumented, f"Root public API missing markdown coverage: {undocumented}"
