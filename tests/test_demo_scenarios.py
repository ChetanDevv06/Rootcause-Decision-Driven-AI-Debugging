"""Tests for the Rootcause demo scenarios feature.

Covers:
- Scenario registry correctness (unique ids, stable list)
- Fixture directories exist and reproduce their intended failure
- Scenario selection returns the correct project path and error input
- FastAPI /api/demo-scenarios endpoints respond correctly
- Diagnostic tools collect expected evidence for each scenario
- No credentials or sensitive values leak into scenario errors
- Existing sample traceback / investigation behaviour remains intact
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.config import TargetProjectConfig
from src.demo_scenarios import (
    ExpectedOutcome,
    DemoScenario,
    expected_outcomes,
    fixture_absolute_path,
    get_scenario,
    list_scenarios,
    scenario_ids,
    SCENARIOS,
)
from src.diagnostics import inspect_dependencies, inspect_source
from src.orchestrator import execute_action


REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_fixture_tests(fixture_dir: Path) -> subprocess.CompletedProcess:
    """Run a fixture's test_fixture.py and return the completed process."""
    return subprocess.run(
        [sys.executable, "test_fixture.py"],
        cwd=str(fixture_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Scenario registry correctness
# ---------------------------------------------------------------------------


def test_list_scenarios_returns_registered_count():
    """The registry exposes all registered scenarios with unique ids."""
    scenarios = list_scenarios()
    assert len(scenarios) >= 6, "Expected at least six demo scenarios"
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids)), "Scenario ids must be unique"
    assert set(ids) == set(scenario_ids())


def test_scenario_has_required_fields():
    """Every scenario has a non-empty name, category, description, error."""
    for scenario in list_scenarios():
        assert scenario.id
        assert scenario.name
        assert scenario.category
        assert scenario.description
        assert scenario.error
        assert scenario.fixture_dir
        assert isinstance(scenario.expected_outcome, ExpectedOutcome)


def test_expected_outcomes_match_scenarios():
    """expected_outcomes() mirrors the scenario registry."""
    outcomes = expected_outcomes()
    assert len(outcomes) == len(list_scenarios())
    by_id = {o.scenario_id: o for o in outcomes}
    for scenario in list_scenarios():
        assert scenario.id in by_id
        assert by_id[scenario.id].failure_category == scenario.category


# ---------------------------------------------------------------------------
# Fixture existence and reproduction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_scenario_fixture_directory_exists(scenario_id: str):
    """Every scenario points to a real fixture directory."""
    scenario = get_scenario(scenario_id)
    assert scenario is not None
    path = fixture_absolute_path(scenario, REPO_ROOT)
    assert path.is_dir(), f"Fixture directory missing for {scenario_id}: {path}"


@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_each_fixture_reproduces_its_failure(scenario_id: str):
    """Running the fixture's test_fixture.py must reproduce the intended failure."""
    scenario = get_scenario(scenario_id)
    assert scenario is not None
    fixture_dir = fixture_absolute_path(scenario, REPO_ROOT)
    test_file = fixture_dir / "test_fixture.py"
    assert test_file.is_file(), f"Missing test_fixture.py for {scenario_id}"

    result = _run_fixture_tests(fixture_dir)
    assert result.returncode == 0, (
        f"Fixture {scenario_id} did not reproduce its failure.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "All reproduction tests passed!" in result.stdout


# ---------------------------------------------------------------------------
# Scenario selection returns correct inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_get_scenario_returns_correct_inputs(scenario_id: str):
    """get_scenario returns the scenario with a valid project path and error."""
    scenario = get_scenario(scenario_id)
    assert scenario is not None
    assert scenario.error
    expected_path = str(fixture_absolute_path(scenario, REPO_ROOT))
    # The path must resolve to the fixture directory and exist.
    assert Path(expected_path).is_dir()


def test_get_scenario_unknown_returns_none():
    """get_scenario returns None for an unknown id."""
    assert get_scenario("does_not_exist") is None


# ---------------------------------------------------------------------------
# FastAPI demo scenarios endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(app)


def test_demo_scenarios_list_endpoint(client):
    """GET /api/demo-scenarios returns all scenarios with resolved project paths."""
    res = client.get("/api/demo-scenarios")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "scenarios" in data
    scenarios = data["scenarios"]
    assert len(scenarios) == len(list_scenarios())
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids))

    for entry in scenarios:
        assert set(entry.keys()) >= {
            "id", "name", "category", "description", "fixture_dir",
            "project_path", "error", "expected_outcome",
        }
        assert Path(entry["project_path"]).is_dir()
        assert entry["error"]
        eo = entry["expected_outcome"]
        assert set(eo.keys()) >= {
            "scenario_id", "failure_category", "expected_evidence",
            "expected_diagnosis_category", "suggested_corrective_action",
            "supported", "limitations",
        }


def test_demo_scenario_by_id_endpoint(client):
    """GET /api/demo-scenarios/{id} returns the matching scenario."""
    first_id = scenario_ids()[0]
    res = client.get(f"/api/demo-scenarios/{first_id}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["id"] == first_id
    assert data["project_path"]
    assert data["error"]


def test_demo_scenario_by_id_unknown_404(client):
    """GET /api/demo-scenarios/{unknown} returns 404."""
    res = client.get("/api/demo-scenarios/no_such_scenario")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# No credentials or sensitive values leak into scenario errors
# ---------------------------------------------------------------------------


def test_no_credentials_in_scenario_errors():
    """Scenario error text must not contain secrets, keys, or production paths."""
    secret_patterns = [
        "sk-", "ghp_", "glpat-", "xoxb-",
        "password=", "PASSWORD=", "secret=", "SECRET=",
        "DATABASE_URL=", "AWS_SECRET", "API_KEY=",
        "postgresql://user:pass@", "user:pass@",
    ]
    for scenario in list_scenarios():
        text = scenario.error
        for pat in secret_patterns:
            assert pat.lower() not in text.lower(), (
                f"Scenario {scenario.id} error contains sensitive pattern {pat!r}"
            )


# ---------------------------------------------------------------------------
# Diagnostic tools collect expected evidence per scenario
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_diagnostic_tools_collect_expected_evidence(scenario_id: str):
    """inspect_source / inspect_dependencies gather evidence for each fixture."""
    scenario = get_scenario(scenario_id)
    assert scenario is not None
    fixture_dir = fixture_absolute_path(scenario, REPO_ROOT)
    config = TargetProjectConfig(str(fixture_dir))

    dep_result = inspect_dependencies(config)
    source_result = inspect_source(config)

    # inspect_source should always read at least the app source file(s).
    assert source_result["action"] == "inspect_source"
    assert len(source_result["files_found"]) >= 1, (
        f"Scenario {scenario_id}: inspect_source read no Python files"
    )

    # Concatenate all gathered source text for evidence checks.
    gathered_source = "\n".join(source_result["files_found"].values())
    gathered_deps = "\n".join(dep_result["files_found"].values())

    # Each scenario's expected evidence should be reflected in what the tools
    # can actually observe (source and/or dependency manifests).
    for evidence in scenario.expected_outcome.expected_evidence:
        lowered = evidence.lower()
        combined = (gathered_source + "\n" + gathered_deps).lower()
        # Loose keyword match: at least one distinctive token from each evidence
        # item should appear in the gathered diagnostic output.
        tokens = [t for t in lowered.split() if len(t) > 3]
        assert any(token in combined for token in tokens), (
            f"Scenario {scenario_id}: expected evidence not observed: {evidence!r}"
        )


def test_check_dependency_derives_module_from_missing_dependency_error():
    """check_dependency derives 'psycopg' from the missing_dependency error."""
    scenario = get_scenario("missing_dependency")
    assert scenario is not None
    config = TargetProjectConfig(str(fixture_absolute_path(scenario, REPO_ROOT)))
    result = execute_action(
        "check_dependency",
        config,
        arguments={},
        error=scenario.error,
    )
    assert result["status"] == "missing"
    assert result["module"] == "psycopg"


def test_check_dependency_insufficient_context_when_no_module():
    """check_dependency returns insufficient_context when no module is derivable."""
    scenario = get_scenario("missing_env")
    assert scenario is not None
    config = TargetProjectConfig(str(fixture_absolute_path(scenario, REPO_ROOT)))
    result = execute_action(
        "check_dependency",
        config,
        arguments={},
        error=scenario.error,
    )
    assert result["status"] == "insufficient_context"


# ---------------------------------------------------------------------------
# Existing behaviour remains intact
# ---------------------------------------------------------------------------


def test_sample_traceback_constant_unchanged():
    """The frontend sample traceback constant remains defined (integration smoke)."""
    # Import the frontend source as text and confirm the sample traceback is present.
    frontend_app = REPO_ROOT / "frontend" / "src" / "App.tsx"
    text = frontend_app.read_text(encoding="utf-8")
    assert "ModuleNotFoundError: No module named 'psycopg'" in text
    assert "loadSampleTraceback" in text


def test_investigation_endpoint_still_works(client):
    """Existing /api/investigations endpoint still accepts a real fixture path."""
    scenario = get_scenario("missing_dependency")
    assert scenario is not None
    project_path = str(fixture_absolute_path(scenario, REPO_ROOT))

    fake_result = {
        "project_path": project_path,
        "reported_error": scenario.error,
        "steps_completed": 1,
        "actions_executed": ["inspect_dependencies"],
        "evidence_history": ["inspect_dependencies: requirements.txt declares psycopg"],
        "history": [
            {
                "step": 1,
                "decision": {"action": "inspect_dependencies"},
                "result": {
                    "action": "inspect_dependencies",
                    "files_found": {"requirements.txt": "psycopg[binary]>=3.2"},
                    "status": "ok",
                },
            }
        ],
        "stop_reason": "investigation_finished",
        "analysis": None,
    }

    with patch("src.api.investigate", return_value=fake_result):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": project_path,
                "error": scenario.error,
            },
        )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["project_path"] == project_path
    assert data["reported_error"] == scenario.error
    assert data["steps_completed"] == 1
    assert "analysis" in data
    assert "analysis_status" in data
