import ast
import json
from pathlib import Path

import polars_baseball as pb
from polars_baseball.client import BaseballClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_NOTEBOOKS_DIR = _PROJECT_ROOT / "notebooks"


def _load_notebook_code_cells(notebook_path: Path) -> list[str]:
    data = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells: list[str] = []
    for cell in data.get("cells", []):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if source.strip():
                code_cells.append(source)
    return code_cells


def test_notebooks_exist() -> None:
    notebook_files = list(_NOTEBOOKS_DIR.glob("*.ipynb"))
    assert len(notebook_files) >= 3, f"Expected at least 3 notebooks in {_NOTEBOOKS_DIR}"


def test_notebook_code_cells_are_syntactically_valid() -> None:
    for nb_path in _NOTEBOOKS_DIR.glob("*.ipynb"):
        cells = _load_notebook_code_cells(nb_path)
        for idx, code in enumerate(cells, 1):
            # Transform top-level await to valid syntax for ast parsing
            # Jupyter allows top-level await; in standard Python AST we wrap in async def
            wrapped = f"async def _cell_{idx}():\n" + "\n".join(f"    {line}" for line in code.splitlines())
            try:
                ast.parse(wrapped)
            except SyntaxError as exc:
                raise AssertionError(f"Syntax error in {nb_path.name} cell {idx}: {exc}") from exc


def _extract_attr_chain(node: ast.Attribute) -> tuple[str, list[str]] | None:
    parts = [node.attr]
    val = node.value
    while isinstance(val, ast.Attribute):
        parts.append(val.attr)
        val = val.value
    if not isinstance(val, ast.Name):
        return None
    return val.id, list(reversed(parts))


def _resolve_chain(symbol: object, chain: list[str]) -> bool:
    curr = symbol
    for attr in chain:
        if not hasattr(curr, attr):
            return False
        curr = getattr(curr, attr)
    return True


def _check_cell_node(
    node: ast.AST,
    package_aliases: set[str],
    client_var_names: set[str],
    client: BaseballClient,
    nb_name: str,
    idx: int,
) -> str | None:
    if not isinstance(node, ast.Attribute):
        return None
    extracted = _extract_attr_chain(node)
    if extracted is None:
        return None
    root_var, chain = extracted

    if root_var in package_aliases and not _resolve_chain(pb, chain):
        return f"{nb_name} [cell {idx}]: pb.{'.'.join(chain)} is invalid"
    if root_var in client_var_names and not _resolve_chain(client, chain):
        return f"{nb_name} [cell {idx}]: client.{'.'.join(chain)} is invalid"
    return None


def test_notebook_attributes_resolve_strictly() -> None:
    client = BaseballClient()
    failures: list[str] = []

    for nb_path in _NOTEBOOKS_DIR.glob("*.ipynb"):
        cells = _load_notebook_code_cells(nb_path)
        package_aliases: set[str] = set()
        client_var_names: set[str] = {"client", "pb_client"}

        for idx, code in enumerate(cells, 1):
            wrapped = f"async def _cell_{idx}():\n" + "\n".join(f"    {line}" for line in code.splitlines())
            tree = ast.parse(wrapped)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "polars_baseball":
                            package_aliases.add(alias.asname or alias.name)

            for node in ast.walk(tree):
                err = _check_cell_node(node, package_aliases, client_var_names, client, nb_path.name, idx)
                if err:
                    failures.append(err)

    assert not failures, "Broken API calls in notebooks:\n" + "\n".join(failures)
