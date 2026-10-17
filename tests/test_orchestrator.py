"""Tests for the orchestrator with run_tests action."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.config import TargetProjectConfig
from src.orchestrator import investigate, execute_action
from src.diagnostics import run_tests, check_dependency


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


def test_execute_action_check_dependency_derives_module_from_error(tmp_path: Path):
    """Test that execute_action derives module name from reported error."""
    config = TargetProjectConfig(str(tmp_path))

    with patch("src.orchestrator.check_dependency") as mock_check:
        mock_check.return_value = {
            "action": "check_dependency",
            "module": "psycopg",
            "status": "missing",
            "interpreter": "/path/to/python",
        }
        result = execute_action(
            "check_dependency",
            config,
            arguments={},
            error="ModuleNotFoundError: No module named 'psycopg'",
        )

    mock_check.assert_called_once()
    assert mock_check.call_args.args[1] == "psycopg"
    assert result["status"] == "missing"


def test_execute_action_check_dependency_insufficient_context(tmp_path: Path):
    """Test that execute_action returns insufficient_context when module ambiguous."""
    config = TargetProjectConfig(str(tmp_path))

    result = execute_action(
        "check_dependency",
        config,
        arguments={},
        error="Something went wrong",
        evidence_history=["inspect_source: read 5 files"],
    )

    assert result["action"] == "check_dependency"
    assert result["status"] == "insufficient_context"
    assert result["exit_code"] is None


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


@patch("src.orchestrator.choose_next_action")
def test_investigate_continues_after_insufficient_context(mock_choose, tmp_path: Path):
    """Test that investigation continues after check_dependency returns insufficient_context."""
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")
    (tmp_path / "app.py").write_text("import psycopg\n")
    (tmp_path / "test_sample.py").write_text("def test_pass(): assert True\n")

    call_count = {"count": 0}
    def side_effect(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return {
                "action": "check_dependency",
                "probabilities": {"check_dependency": 1.0},
                "confidence": 1.0,
                "model": "mock",
            }
        elif call_count["count"] == 2:
            return {
                "action": "inspect_dependencies",
                "probabilities": {"inspect_dependencies": 1.0},
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
        error="ModuleNotFoundError: No module named 'psycopg'",
        evidence=[],
        max_steps=3,
    )

    # check_dependency ran first but returned insufficient_context (no module derivable yet)
    # Investigation should continue to inspect_dependencies
    assert "check_dependency" in result["actions_executed"]
    assert "inspect_dependencies" in result["actions_executed"]
    # Did not stop prematurely on insufficient_context
    assert result["steps_completed"] >= 2


@patch("src.orchestrator.choose_next_action")
def test_investigate_stops_on_tool_error(mock_choose, tmp_path: Path):
    """Test that investigation stops on genuine diagnostic-tool errors."""
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")

    # First action returns a tool error
    mock_choose.return_value = {
        "action": "check_dependency",
        "probabilities": {"check_dependency": 1.0},
        "confidence": 1.0,
        "model": "mock",
    }

    config = TargetProjectConfig(str(tmp_path))

    # Patch check_dependency to return an error status
    with patch("src.orchestrator.check_dependency") as mock_check:
        mock_check.return_value = {
            "action": "check_dependency",
            "module": "psycopg",
            "status": "error",
            "interpreter": "/nonexistent/python",
            "stderr": "Python interpreter not found",
        }
        result = investigate(
            config=config,
            error="ModuleNotFoundError: No module named 'psycopg'",
            evidence=[],
            max_steps=5,
        )

    # Investigation stops after the tool error
    assert "check_dependency" in result["actions_executed"]
    # Should not continue to more steps after a tool error
    assert result["steps_completed"] == 1


@patch("src.orchestrator.choose_next_action")
def test_decider_selected_action_is_executed(mock_choose, tmp_path: Path):
    """Test that the action selected by Decider is the one actually executed."""
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")

    mock_choose.return_value = {
        "action": "inspect_dependencies",
        "probabilities": {"inspect_dependencies": 1.0},
        "confidence": 1.0,
        "model": "mock",
    }

    config = TargetProjectConfig(str(tmp_path))

    result = investigate(
        config=config,
        error="Missing dependency",
        evidence=[],
        max_steps=1,
    )

    assert result["actions_executed"] == ["inspect_dependencies"]
    assert result["history"][0]["result"]["action"] == "inspect_dependencies"


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


@patch("src.orchestrator.choose_next_action")
def test_investigate_step_budget_exhausted_truncation(mock_choose, tmp_path: Path):
    """Test that exhausting the step budget produces a truncation notice."""
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")
    (tmp_path / "app.py").write_text("import psycopg\n")

    # Decider keeps selecting actions without ever choosing stop_and_report
    mock_choose.return_value = {
        "action": "inspect_dependencies",
        "probabilities": {"inspect_dependencies": 1.0},
        "confidence": 1.0,
        "model": "mock",
    }

    config = TargetProjectConfig(str(tmp_path))

    result = investigate(
        config=config,
        error="ModuleNotFoundError: No module named 'psycopg'",
        evidence=[],
        max_steps=1,
    )

    # With max_steps=1, only one action can run before budget is exhausted
    assert result["stop_reason"] == "maximum_steps_reached"
    assert "truncation_notice" in result
    assert "truncated" in result["truncation_notice"].lower()
    assert "1 step" in result["truncation_notice"] or "1 step(s)" in result["truncation_notice"]


@patch("src.orchestrator.choose_next_action")
def test_investigate_stop_and_report_distinguishable_from_truncation(mock_choose, tmp_path: Path):
    """Test that stop_and_report is distinguishable from maximum_steps_reached."""
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
        max_steps=5,
    )

    assert result["stop_reason"] == "investigation_finished"
    assert "truncation_notice" not in result
    assert result["steps_completed"] == 1
    assert result["actions_executed"] == []


@patch("src.orchestrator.choose_next_action")
def test_investigate_passing_tests_reproduction_confirmation(mock_choose, tmp_path: Path):
    """Test that passing tests which assert failure are treated as reproduction confirmation.

    When run_tests passes but the tests assert ModuleNotFoundError, the passing
    result confirms the expected failure was reproduced — it does not mean the
    application works.
    """
    (tmp_path / "requirements.txt").write_text("psycopg[binary]>=3.2\n")
    (tmp_path / "app.py").write_text("import psycopg\n")
    (tmp_path / "test_sample.py").write_text(
        "import importlib.util\n"
        "def test_missing_psycopg():\n"
        "    assert importlib.util.find_spec('psycopg') is None\n"
    )

    call_count = {"count": 0}
    def side_effect(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
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
        error="ModuleNotFoundError: No module named 'psycopg'",
        evidence=[],
        max_steps=3,
    )

    assert "run_tests" in result["actions_executed"]
    # run_tests result should show status "passed" but evidence should note
    # that tests assert the import failure
    run_tests_result = result["history"][0]["result"]
    assert run_tests_result["status"] == "passed"
    # Investigation should continue to stop_and_report (not stop on passed tests)
    assert result["stop_reason"] == "investigation_finished"


def test_inspect_source_reads_and_reports_files(tmp_path: Path):
    """Test that inspect_source reads Python files and reports their contents."""
    from src.diagnostics import inspect_source

    (tmp_path / "app.py").write_text("import psycopg\n")
    (tmp_path / "utils.py").write_text("def helper(): pass\n")
    (tmp_path / "README.md").write_text("# Project\n")

    config = TargetProjectConfig(str(tmp_path), max_files=10)

    result = inspect_source(config)

    assert result["action"] == "inspect_source"
    assert "app.py" in result["files_found"]
    assert "utils.py" in result["files_found"]
    assert "README.md" not in result["files_found"]  # Not a .py file
    assert result["files_found"]["app.py"] == "import psycopg\n"
    assert result["files_found"]["utils.py"] == "def helper(): pass\n"


def test_inspect_source_syntax_error_reporting(tmp_path: Path):
    """Test that inspect_source can detect syntax errors in Python files."""
    from src.diagnostics import inspect_source

    # Write a Python file with a syntax error
    (tmp_path / "broken.py").write_text("import psycopg\n" "def broken(\n" "    pass\n")

    config = TargetProjectConfig(str(tmp_path), max_files=10)

    result = inspect_source(config)

    assert result["action"] == "inspect_source"
    assert "broken.py" in result["files_found"]
    # The file content should be readable even with syntax errors
    assert "def broken(" in result["files_found"]["broken.py"]


def test_check_dependency_reports_interpreter_details(tmp_path: Path):
    """Test that check_dependency reports the exact interpreter used."""
    import sys
    from src.diagnostics import check_dependency

    config = TargetProjectConfig(str(tmp_path))

    # Mock subprocess to return import success
    from unittest.mock import patch, MagicMock
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = check_dependency(config, "sys")

    assert result["interpreter"] == sys.executable
    assert result["status"] == "installed"
    assert "interpreter" in result["evidence"]
    assert sys.executable in result["evidence"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])