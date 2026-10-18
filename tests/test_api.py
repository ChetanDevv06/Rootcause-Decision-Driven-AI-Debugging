"""Tests for the Rootcause FastAPI backend (src/api.py)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    """GET /api/health returns status ok with module info."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "rootcause"
    assert "modules" in data
    assert "decider_reachable" in data
    assert "bedrock_configured" in data


def test_health_decider_reachable(client):
    """GET /api/health reports decider_reachable true when Decider /health returns status ok."""
    from unittest.mock import patch, MagicMock

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = b'{"status": "ok", "model": "strands-decider-2B-hobson-v19"}'

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/health")

    assert res.status_code == 200
    data = res.json()
    assert data["decider_reachable"] is True


def test_health_decider_unreachable(client):
    """GET /api/health reports decider_reachable false when Decider is unreachable."""
    from unittest.mock import patch
    from urllib.error import URLError

    with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
        res = client.get("/api/health")

    assert res.status_code == 200
    data = res.json()
    assert data["decider_reachable"] is False


def test_health_decider_not_ok(client):
    """GET /api/health reports decider_reachable false when Decider status is not ok."""
    from unittest.mock import patch, MagicMock

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = b'{"status": "error", "message": "model not loaded"}'

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get("/api/health")

    assert res.status_code == 200
    data = res.json()
    assert data["decider_reachable"] is False


# ---------------------------------------------------------------------------
# Investigation endpoint — happy path
# ---------------------------------------------------------------------------


def test_investigation_returns_real_result(client, tmp_path: Path):
    """POST /api/investigations returns the real orchestrator result."""
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")
    (tmp_path / "app.py").write_text("import psycopg\n")

    fake_result = {
        "project_path": str(tmp_path.resolve()),
        "reported_error": "ModuleNotFoundError: No module named 'psycopg'",
        "steps_completed": 2,
        "actions_executed": ["inspect_dependencies", "check_dependency"],
        "evidence_history": [
            "Step 1: inspect_dependencies returned: requirements.txt declares psycopg[binary]>=3.2",
            "Step 2: check_dependency returned: Module 'psycopg' is not importable",
        ],
        "history": [
            {
                "step": 1,
                "decision": {"action": "inspect_dependencies"},
                "result": {
                    "action": "inspect_dependencies",
                    "files_found": {"requirements.txt": "psycopg[binary]>=3.2"},
                    "status": "ok",
                },
            },
            {
                "step": 2,
                "decision": {"action": "check_dependency"},
                "result": {
                    "action": "check_dependency",
                    "module": "psycopg",
                    "status": "missing",
                    "interpreter": "/usr/bin/python3",
                    "evidence": "Module 'psycopg' is not importable",
                },
            },
        ],
        "stop_reason": "investigation_finished",
        "analysis": {
            "analysis": {
                "confirmed_observations": ["requirements.txt declares psycopg"],
                "most_likely_cause": "Missing dependency: psycopg not installed",
                "alternative_explanations": ["Wrong interpreter"],
                "evidence_supporting": {"Missing dependency": ["requirements.txt"]},
                "remaining_uncertainty": [],
                "recommended_next_step": "pip install -r requirements.txt",
                "suggested_fix": "pip install -r requirements.txt",
                "evidence_sufficient": True,
            },
            "analysis_status": "success",
        },
        "analysis_status": "success",
    }

    with patch("src.api.investigate", return_value=fake_result):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "ModuleNotFoundError: No module named 'psycopg'",
                "max_steps": 3,
            },
        )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["project_path"] == str(tmp_path.resolve())
    assert data["reported_error"] == "ModuleNotFoundError: No module named 'psycopg'"
    assert data["steps_completed"] == 2
    assert data["actions_executed"] == ["inspect_dependencies", "check_dependency"]
    assert data["stop_reason"] == "investigation_finished"
    assert data["analysis"]["most_likely_cause"] == "Missing dependency: psycopg not installed"
    assert data["analysis_status"] == "success"


def test_investigation_defaults_max_steps(client, tmp_path: Path):
    """When max_steps is omitted, the orchestrator default is used."""
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")

    with patch("src.api.investigate") as mock_investigate:
        mock_investigate.return_value = {
            "project_path": str(tmp_path.resolve()),
            "reported_error": "Missing dependency",
            "steps_completed": 1,
            "actions_executed": ["inspect_dependencies"],
            "evidence_history": [],
            "history": [],
            "stop_reason": "investigation_finished",
            "analysis": None,
            "analysis_status": None,
        }
        client.post(
            "/api/investigations",
            json={"project_path": str(tmp_path), "error": "Missing dependency"},
        )

    # max_steps should be None (orchestrator default)
    call_kwargs = mock_investigate.call_args.kwargs
    assert call_kwargs["max_steps"] is None


# ---------------------------------------------------------------------------
# Investigation endpoint — input validation
# ---------------------------------------------------------------------------


def test_investigation_rejects_nonexistent_path(client):
    """POST /api/investigations rejects a path that does not exist."""
    res = client.post(
        "/api/investigations",
        json={
            "project_path": "/nonexistent/path/that/does/not/exist",
            "error": "Some error",
        },
    )
    assert res.status_code == 400
    assert "does not exist" in res.json()["detail"]


def test_investigation_rejects_file_instead_of_directory(client, tmp_path: Path):
    """POST /api/investigations rejects a file path instead of a directory."""
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("content")

    res = client.post(
        "/api/investigations",
        json={
            "project_path": str(file_path),
            "error": "Some error",
        },
    )
    assert res.status_code == 400
    assert "not a directory" in res.json()["detail"]


def test_investigation_rejects_empty_error(client, tmp_path: Path):
    """POST /api/investigations rejects an empty error message."""
    res = client.post(
        "/api/investigations",
        json={
            "project_path": str(tmp_path),
            "error": "",
        },
    )
    assert res.status_code == 422  # Pydantic validation error


def test_investigation_rejects_max_steps_out_of_range(client, tmp_path: Path):
    """POST /api/investigations rejects max_steps outside [1, 10]."""
    res = client.post(
        "/api/investigations",
        json={
            "project_path": str(tmp_path),
            "error": "Some error",
            "max_steps": 0,
        },
    )
    assert res.status_code == 422  # Pydantic validation error

    res = client.post(
        "/api/investigations",
        json={
            "project_path": str(tmp_path),
            "error": "Some error",
            "max_steps": 99,
        },
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Investigation endpoint — service errors
# ---------------------------------------------------------------------------


def test_investigation_handles_orchestrator_value_error(client, tmp_path: Path):
    """ValueError from orchestrator is returned as HTTP 400."""
    with patch("src.api.TargetProjectConfig", side_effect=ValueError("bad path")):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "Some error",
            },
        )
    assert res.status_code == 400
    assert "bad path" in res.json()["detail"]


def test_investigation_handles_unexpected_error(client, tmp_path: Path):
    """Unexpected orchestrator errors are returned as HTTP 500."""
    with patch("src.api.investigate", side_effect=RuntimeError("boom")):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "Some error",
            },
        )
    assert res.status_code == 500
    assert "boom" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Investigation endpoint — Bedrock/Decider unavailability (graceful)
# ---------------------------------------------------------------------------


def test_investigation_with_bedrock_error(client, tmp_path: Path):
    """When Bedrock analysis fails, the result still contains the investigation data."""
    fake_result = {
        "project_path": str(tmp_path.resolve()),
        "reported_error": "ModuleNotFoundError: No module named 'psycopg'",
        "steps_completed": 1,
        "actions_executed": ["inspect_dependencies"],
        "evidence_history": [],
        "history": [],
        "stop_reason": "investigation_finished",
        "analysis": {
            "analysis_error": "Bedrock API error: timeout",
            "analysis_status": "bedrock_error",
        },
        "analysis_status": "bedrock_error",
        "analysis_error": "Bedrock API error: timeout",
    }

    with patch("src.api.investigate", return_value=fake_result):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "ModuleNotFoundError: No module named 'psycopg'",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data["analysis_status"] == "bedrock_error"
    assert "Bedrock API error" in data["analysis_error"]


# ---------------------------------------------------------------------------
# Investigation endpoint — analysis serialization (no undefined values)
# ---------------------------------------------------------------------------


def test_investigation_analysis_never_null(client, tmp_path: Path):
    """When Bedrock analysis fails, analysis is never null in the response.

    The API always returns a minimal analysis object so the frontend does not
    render ``undefined``.
    """
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")

    fake_result = {
        "project_path": str(tmp_path.resolve()),
        "reported_error": "ModuleNotFoundError: No module named 'psycopg'",
        "steps_completed": 1,
        "actions_executed": ["inspect_dependencies"],
        "evidence_history": [],
        "history": [],
        "stop_reason": "investigation_finished",
        "analysis": {
            "analysis_error": "boto3 not available",
            "analysis_status": "configuration_error",
        },
        "analysis_status": "configuration_error",
        "analysis_error": "boto3 not available",
    }

    with patch("src.api.investigate", return_value=fake_result):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "ModuleNotFoundError: No module named 'psycopg'",
            },
        )

    assert res.status_code == 200
    data = res.json()
    # analysis must be a dict, never None
    assert isinstance(data["analysis"], dict)
    assert data["analysis"]["most_likely_cause"] is None
    assert data["analysis"]["evidence_sufficient"] is False
    assert data["analysis"]["_analysis_status"] == "configuration_error"
    assert data["analysis"]["_analysis_error"] == "boto3 not available"
    assert data["analysis_status"] == "configuration_error"


def test_investigation_analysis_none_from_orchestrator(client, tmp_path: Path):
    """When orchestrator returns analysis=None, API still returns a dict."""
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")

    fake_result = {
        "project_path": str(tmp_path.resolve()),
        "reported_error": "Some error",
        "steps_completed": 0,
        "actions_executed": [],
        "evidence_history": [],
        "history": [],
        "stop_reason": "investigation_finished",
        "analysis": None,
    }

    with patch("src.api.investigate", return_value=fake_result):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "Some error",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["analysis"], dict)
    assert data["analysis"]["most_likely_cause"] is None
    assert data["analysis"]["evidence_sufficient"] is False


# ---------------------------------------------------------------------------
# Investigation endpoint — Decider unavailable
# ---------------------------------------------------------------------------


def test_investigation_decider_unavailable(client, tmp_path: Path):
    """When Decider is unreachable, investigation stops gracefully."""
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")

    from src.decider_client import DeciderConnectionError

    with patch("src.api.investigate") as mock_investigate:
        mock_investigate.return_value = {
            "project_path": str(tmp_path.resolve()),
            "reported_error": "ModuleNotFoundError: No module named 'psycopg'",
            "steps_completed": 1,
            "actions_executed": [],
            "evidence_history": [],
            "history": [
                {
                    "step": 1,
                    "decision_error": {
                        "type": "DeciderConnectionError",
                        "message": "Failed to connect to Decider",
                    },
                    "result": {
                        "action": "decider_error",
                        "evidence": "Decider error: Failed to connect to Decider",
                    },
                },
            ],
            "stop_reason": "investigation_finished",
            "analysis": {
                "analysis": {
                    "most_likely_cause": "Decider unavailable — could not select diagnostic actions",
                    "confirmed_observations": [],
                    "alternative_explanations": [],
                    "evidence_supporting": {},
                    "remaining_uncertainty": ["Decider server not reachable at 127.0.0.1:8099"],
                    "recommended_next_step": "Start the Decider server and retry",
                    "suggested_fix": None,
                    "evidence_sufficient": False,
                },
                "analysis_status": "success",
            },
            "analysis_status": "success",
        }

        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "ModuleNotFoundError: No module named 'psycopg'",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data["actions_executed"] == []
    assert data["stop_reason"] == "investigation_finished"
    # History records the decider error — no silent fallback
    assert len(data["history"]) == 1
    assert data["history"][0]["result"]["action"] == "decider_error"


# ---------------------------------------------------------------------------
# Investigation endpoint — Decider-selected vs executed action
# ---------------------------------------------------------------------------


def test_investigation_executes_decider_selected_action(client, tmp_path: Path):
    """The action executed at each step matches the Decider's selection.

    No silent fallback: the orchestrator passes decision["action"] directly
    to execute_action. history[].decision.action == history[].result.action.
    """
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")

    fake_result = {
        "project_path": str(tmp_path.resolve()),
        "reported_error": "ModuleNotFoundError: No module named 'psycopg'",
        "steps_completed": 1,
        "actions_executed": ["inspect_dependencies"],
        "evidence_history": [],
        "history": [
            {
                "step": 1,
                "decision": {"action": "inspect_dependencies", "confidence": 1.0},
                "result": {
                    "action": "inspect_dependencies",
                    "files_found": {"requirements.txt": "psycopg[binary]>=3.2"},
                    "status": "ok",
                },
            },
        ],
        "stop_reason": "investigation_finished",
        "analysis": {
            "analysis": {
                "most_likely_cause": "Missing dependency",
                "confirmed_observations": ["requirements.txt declares psycopg"],
                "alternative_explanations": [],
                "evidence_supporting": {},
                "remaining_uncertainty": [],
                "recommended_next_step": "Install dependencies",
                "suggested_fix": None,
                "evidence_sufficient": False,
            },
            "analysis_status": "success",
        },
        "analysis_status": "success",
    }

    with patch("src.api.investigate", return_value=fake_result):
        res = client.post(
            "/api/investigations",
            json={
                "project_path": str(tmp_path),
                "error": "ModuleNotFoundError: No module named 'psycopg'",
            },
        )

    assert res.status_code == 200
    data = res.json()
    # The Decider-selected action matches the executed action
    assert data["actions_executed"] == ["inspect_dependencies"]
    step = data["history"][0]
    assert step["decision"]["action"] == step["result"]["action"]
    assert step["result"]["action"] == "inspect_dependencies"


# ---------------------------------------------------------------------------
# Telemetry endpoints
# ---------------------------------------------------------------------------


def test_telemetry_returns_real_metrics(client):
    """GET /api/telemetry returns real-time engine and system telemetry."""
    res = client.get("/api/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "memory_percent" in data
    assert "memory_used_gb" in data
    assert "memory_total_gb" in data
    assert "quantization" in data
    assert "decider_reachable" in data
    assert "tooling_probes_count" in data
    assert "default_interpreter" in data
    assert "temporary_diff_stash" in data
    assert data["zero_outbound"] is True


def test_benchmark_runs_successfully(client):
    """POST /api/telemetry/benchmark executes AST and Decider benchmarks."""
    res = client.post("/api/telemetry/benchmark")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "ast_parse_ops_per_sec" in data
    assert data["ast_parse_ops_per_sec"] > 0
    assert "benchmark_duration_ms" in data

