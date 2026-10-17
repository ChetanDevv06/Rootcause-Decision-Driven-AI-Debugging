"""Tests for the orchestrator with run_tests action."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.config import TargetProjectConfig
from src.orchestrator import investigate, execute_action
from src.diagnostics import run_tests


class MockDeciderResponse:
    """Mock response from the Decider API."""
    def __init__(self, action: str):
        self.action = action


def test_execute_action_run_tests(tmp_path: Path):
    """Test that execute_action routes run_tests correctly."""
    (tmp_path / "test_sample.py").write_text("def test_pass(): assert True\n")

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_sample.py", "-v"],
        test_timeout=30,
    )

    result = execute_action("run_tests", config)

    assert result["action"] == "run_tests"
    assert result["project_path"] == str(tmp_path.resolve())
    assert "exit_code" in result


def test_execute_action_rejects_unknown(tmp_path: Path):
    """Test that execute_action rejects unknown actions."""
    config = TargetProjectConfig(str(tmp_path))

    try:
        execute_action("unknown_action", config)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unsupported diagnostic action" in str(exc)


@patch("src.orchestrator.choose_next_action")
def test_investigate_run_tests_selected(mock_choose, tmp_path: Path):
    """Test that when Decider selects run_tests, it executes correctly."""
    (tmp_path / "test_sample.py").write_text("def test_pass(): assert True\n")

    # Mock Decider to return run_tests
    mock_choose.return_value = {
        "action": "run_tests",
        "probabilities": {"run_tests": 1.0},
        "confidence": 1.0,
        "model": "mock",
    }

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_sample.py", "-v"],
        test_timeout=30,
    )

    result = investigate(
        config=config,
        error="Tests are failing",
        evidence=["Test suite has not been run yet."],
        max_steps=2,
    )

    assert result["project_path"] == str(tmp_path.resolve())
    assert "run_tests" in result["actions_executed"]
    assert any("run_tests" in str(step) for step in result["history"])


@patch("src.orchestrator.choose_next_action")
def test_investigate_other_actions_not_run_tests(mock_choose, tmp_path: Path):
    """Test that other Decider selections don't accidentally run tests."""
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")

    # Mock Decider to return inspect_dependencies
    mock_choose.return_value = {
        "action": "inspect_dependencies",
        "probabilities": {"inspect_dependencies": 1.0},
        "confidence": 1.0,
        "model": "mock",
    }

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "-v"],
        test_timeout=30,
    )

    result = investigate(
        config=config,
        error="Missing dependency",
        evidence=["Requirements not inspected."],
        max_steps=2,
    )

    assert result["project_path"] == str(tmp_path.resolve())
    assert "run_tests" not in result["actions_executed"]
    assert "inspect_dependencies" in result["actions_executed"]


@patch("src.orchestrator.choose_next_action")
def test_investigate_stop_and_report(mock_choose, tmp_path: Path):
    """Test that stop_and_report stops the investigation."""
    mock_choose.return_value = {
        "action": "stop_and_report",
        "probabilities": {"stop_and_report": 1.0},
        "confidence": 1.0,
        "model": "mock",
    }

    config = TargetProjectConfig(str(tmp_path))

    result = investigate(
        config=config,
        error="Some error",
        evidence=[],
        max_steps=3,
    )

    assert result["steps_completed"] == 1
    assert result["actions_executed"] == []
    assert result["stop_reason"] == "investigation_finished"


@patch("src.orchestrator.choose_next_action")
def test_investigate_runs_multiple_actions(mock_choose, tmp_path: Path):
    """Test that investigation runs multiple different actions."""
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")
    (tmp_path / "test_sample.py").write_text("def test_pass(): assert True\n")

    # Mock Decider to return different actions in sequence
    call_count = {"count": 0}
    def side_effect(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return {
                "action": "inspect_dependencies",
                "probabilities": {"inspect_dependencies": 1.0},
                "confidence": 1.0,
                "model": "mock",
            }
        elif call_count["count"] == 2:
            return {
                "action": "run_tests",
                "probabilities": {"run_tests": 1.0},
                "confidence": 1.0,
                "model": "mock",
            }
        else:
            return {
                "action": "stop_and_report",
                "probabilities": {"stop_and_report": 1.0},
                "confidence": 1.0,
                "model": "mock",
            }

    mock_choose.side_effect = side_effect

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_sample.py", "-v"],
        test_timeout=30,
    )

    result = investigate(
        config=config,
        error="Test failure",
        evidence=[],
        max_steps=3,
    )

    assert len(result["actions_executed"]) >= 2
    assert "inspect_dependencies" in result["actions_executed"]
    assert "run_tests" in result["actions_executed"]


def test_run_tests_safety_environment_filtering(tmp_path: Path):
    """Test that environment filtering removes sensitive keys."""
    import os
    from src.diagnostics import _filter_environment

    # Set some test environment variables
    os.environ["TEST_SAFE_VAR"] = "safe_value"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "secret"
    os.environ["GITHUB_TOKEN"] = "token"

    try:
        env = _filter_environment()
        assert "AWS_SECRET_ACCESS_KEY" not in env
        assert "GITHUB_TOKEN" not in env
        # Safe vars should be preserved if in SAFE_ENV_KEYS
    finally:
        # Clean up
        os.environ.pop("TEST_SAFE_VAR", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        os.environ.pop("GITHUB_TOKEN", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])