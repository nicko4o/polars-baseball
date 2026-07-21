from __future__ import annotations

from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _PROJECT_ROOT / ".github" / "workflows"


def _load_workflow(name: str) -> dict:
    path = _WORKFLOWS_DIR / name
    assert path.exists(), f"Missing workflow: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_all_workflows_parse_valid_yaml() -> None:
    for path in sorted(_WORKFLOWS_DIR.glob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(doc, dict), f"{path.name} is not a valid YAML mapping"
        assert "name" in doc, f"{path.name} missing top-level 'name'"
        assert "jobs" in doc, f"{path.name} missing 'jobs'"


def test_pytest_workflow_concurrency_group() -> None:
    doc = _load_workflow("pytest.yml")
    assert "concurrency" in doc, "pytest.yml should define concurrency group"


def test_pytest_workflow_concurrency_cancel() -> None:
    doc = _load_workflow("pytest.yml")
    assert doc.get("concurrency", {}).get("cancel-in-progress") is True


def test_pytest_workflow_has_lint_job() -> None:
    doc = _load_workflow("pytest.yml")
    jobs = doc.get("jobs", {})
    assert "lint" in jobs, "pytest.yml should have a 'lint' job"


def test_pytest_workflow_test_needs_lint() -> None:
    doc = _load_workflow("pytest.yml")
    jobs = doc.get("jobs", {})
    assert "test" in jobs
    assert "lint" in jobs["test"].get("needs", []), "test job must depend on lint"


def test_pytest_workflow_lint_skips_matrix() -> None:
    doc = _load_workflow("pytest.yml")
    lint = doc.get("jobs", {}).get("lint", {})
    strategy = lint.get("strategy", {})
    assert "matrix" not in strategy, "lint job should not use Python version matrix"


def test_pytest_workflow_lint_includes_uv_audit() -> None:
    doc = _load_workflow("pytest.yml")
    lint = doc.get("jobs", {}).get("lint", {})
    steps = lint.get("steps", [])
    step_names = [s.get("name", "") for s in steps]
    assert any("uv audit" in n.lower() or "audit" in n.lower() for n in step_names), (
        "lint job missing dependency audit step"
    )


def test_pytest_workflow_lint_includes_examples_check() -> None:
    doc = _load_workflow("pytest.yml")
    lint = doc.get("jobs", {}).get("lint", {})
    steps = lint.get("steps", [])
    step_names = [s.get("name", "") for s in steps]
    assert any("example" in n.lower() for n in step_names), "lint job missing examples syntax check step"


def test_nightly_workflow_has_concurrency() -> None:
    doc = _load_workflow("nightly-contract.yml")
    assert "concurrency" in doc


def test_verify_apis_workflow_has_concurrency() -> None:
    doc = _load_workflow("verify-apis.yml")
    assert "concurrency" in doc


def test_compile_datasets_workflow_has_concurrency() -> None:
    doc = _load_workflow("compile-datasets.yml")
    assert "concurrency" in doc


def test_publish_workflow_build_reuse() -> None:
    doc = _load_workflow("python-publish.yml")
    jobs = doc.get("jobs", {})
    validate = jobs.get("validate", {})
    deploy = jobs.get("deploy", {})

    validate_steps = [s.get("name", "") for s in validate.get("steps", [])]
    deploy_steps = [s.get("name", "") for s in deploy.get("steps", [])]

    assert any("Upload" in n for n in validate_steps), "validate job should upload dist/ as artifact"
    assert any("Download" in n for n in deploy_steps), "deploy job should download dist/ artifact"
    assert not any("Install dependencies" in n for n in deploy_steps), "deploy job should not reinstall dependencies"


def test_publish_workflow_validate_skips_redundant_sync() -> None:
    doc = _load_workflow("python-publish.yml")
    validate = doc.get("jobs", {}).get("validate", {})
    steps_text = " ".join(s.get("run", "") for s in validate.get("steps", []) if s.get("run"))
    sync_count = steps_text.count("uv sync")
    assert sync_count <= 1, f"validate job runs uv sync {sync_count} times (expected <=1)"


def test_codecov_config_exists() -> None:
    path = _PROJECT_ROOT / "codecov.yml"
    assert path.exists(), "Missing codecov.yml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    patch_default = doc.get("coverage", {}).get("status", {}).get("patch", {}).get("default", {})
    assert patch_default.get("target") is not None, "codecov.yml must set patch target"


def test_codecov_patch_target_configured() -> None:
    path = _PROJECT_ROOT / "codecov.yml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    patch_target = doc["coverage"]["status"]["patch"]["default"]["target"]
    assert patch_target in ("auto", 90) or isinstance(patch_target, (int, float))
