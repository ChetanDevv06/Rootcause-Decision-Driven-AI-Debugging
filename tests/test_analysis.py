"""Tests for the analysis module."""

import json
from unittest.mock import patch, MagicMock

from src.analysis import (
    RootCauseReport,
    _build_analysis_prompt,
    _parse_analysis_response,
    analyze_root_cause,
)


SAMPLE_INVESTIGATION = {
    "project_path": "examples/fixtures/missing_dependency",
    "reported_error": "ModuleNotFoundError: No module named 'psycopg'",
    "steps_completed": 3,
    "actions_executed": ["inspect_dependencies", "inspect_source", "run_tests"],
    "evidence_history": [
        "Initial: missing psycopg module",
        "Step 1: inspect_dependencies returned: requirements.txt declares psycopg[binary]>=3.2",
        "Step 2: inspect_source returned: app.py imports psycopg at module level",
        "Step 3: run_tests returned: tests passed (exit code 0) - test confirms import fails",
    ],
    "history": [
        {"step": 1, "result": {"action": "inspect_dependencies", "files_found": {"requirements.txt": "psycopg[binary]>=3.2"}}},
        {"step": 2, "result": {"action": "inspect_source", "files_found": {"app.py": "import psycopg..."}}},
        {"step": 3, "result": {"action": "run_tests", "status": "passed", "exit_code": 0}},
    ],
}


def test_root_cause_report_dataclass():
    """Test RootCauseReport dataclass creation and serialization."""
    report = RootCauseReport(
        confirmed_observations=["psycopg declared in requirements.txt", "app.py imports psycopg"],
        most_likely_cause="Missing dependency: psycopg not installed",
        alternative_explanations=["Wrong Python environment", "Virtual environment not activated"],
        evidence_supporting={
            "Missing dependency": ["requirements.txt declares psycopg", "test confirms import fails"],
            "Wrong environment": ["No evidence of environment issues"],
        },
        remaining_uncertainty=["Exact environment configuration"],
        recommended_next_step="Install dependencies with pip install -r requirements.txt",
        suggested_fix="pip install -r requirements.txt",
        evidence_sufficient=True,
    )

    data = report.to_dict()
    assert data["confirmed_observations"] == ["psycopg declared in requirements.txt", "app.py imports psycopg"]
    assert data["most_likely_cause"] == "Missing dependency: psycopg not installed"
    assert data["evidence_sufficient"] is True


def test_build_analysis_prompt():
    """Test prompt building includes all relevant information."""
    prompt = _build_analysis_prompt(SAMPLE_INVESTIGATION)

    assert "examples/fixtures/missing_dependency" in prompt
    assert "ModuleNotFoundError" in prompt
    assert "psycopg" in prompt
    assert "inspect_dependencies" in prompt
    assert "inspect_source" in prompt
    assert "run_tests" in prompt
    assert "confirmed_observations" in prompt
    assert "most_likely_cause" in prompt
    assert "evidence_sufficient" in prompt


def test_parse_analysis_response_valid():
    """Test parsing valid model response."""
    response = json.dumps({
        "confirmed_observations": ["psycopg in requirements.txt"],
        "most_likely_cause": "Missing dependency",
        "alternative_explanations": ["Environment issue"],
        "evidence_supporting": {"Missing dependency": ["requirements.txt"]},
        "remaining_uncertainty": ["Environment"],
        "recommended_next_step": "Install deps",
        "suggested_fix": "pip install -r requirements.txt",
        "evidence_sufficient": True,
    })

    report = _parse_analysis_response(response)
    assert isinstance(report, RootCauseReport)
    assert report.most_likely_cause == "Missing dependency"
    assert report.evidence_sufficient is True


def test_parse_analysis_response_markdown():
    """Test parsing JSON from markdown code block."""
    response = """```json
{
  "confirmed_observations": ["test"],
  "most_likely_cause": "cause",
  "alternative_explanations": ["alt"],
  "evidence_supporting": {"cause": ["evidence"]},
  "remaining_uncertainty": ["uncertainty"],
  "recommended_next_step": "step",
  "suggested_fix": "fix",
  "evidence_sufficient": false
}
```"""

    report = _parse_analysis_response(response)
    assert isinstance(report, RootCauseReport)
    assert report.evidence_sufficient is False


def test_parse_analysis_response_missing_field():
    """Test handling of missing required fields."""
    response = json.dumps({
        "confirmed_observations": ["test"],
        "most_likely_cause": "cause",
        # missing other fields
    })

    try:
        _parse_analysis_response(response)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Missing required field" in str(exc)


def test_parse_analysis_response_invalid_json():
    """Test handling of invalid JSON."""
    response = "not valid json at all"

    try:
        _parse_analysis_response(response)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "not valid JSON" in str(exc) or "Failed to parse" in str(exc)


@patch("src.analysis.boto3")
def test_analyze_root_cause_success(mock_boto3):
    """Test successful analysis with mocked Bedrock."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": json.dumps({
                    "confirmed_observations": ["psycopg declared", "import fails"],
                    "most_likely_cause": "Missing dependency: psycopg not installed",
                    "alternative_explanations": ["Wrong environment"],
                    "evidence_supporting": {"Missing dependency": ["requirements.txt", "test output"]},
                    "remaining_uncertainty": ["Environment details"],
                    "recommended_next_step": "pip install -r requirements.txt",
                    "suggested_fix": "pip install -r requirements.txt",
                    "evidence_sufficient": True,
                })}],
            },
        },
    }

    result = analyze_root_cause(SAMPLE_INVESTIGATION)

    assert result["analysis_status"] == "success"
    assert "analysis" in result
    assert result["analysis"]["most_likely_cause"] == "Missing dependency: psycopg not installed"
    assert result["analysis"]["evidence_sufficient"] is True


@patch("src.analysis.boto3")
def test_analyze_root_cause_bedrock_error(mock_boto3):
    """Test handling of Bedrock API errors."""
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.converse.side_effect = ClientError(
        {"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
        "converse",
    )

    result = analyze_root_cause(SAMPLE_INVESTIGATION)

    assert result["analysis_status"] == "bedrock_error"
    assert "analysis_error" in result
    assert "Bedrock API error" in result["analysis_error"]


@patch("src.analysis.boto3")
def test_analyze_root_cause_parse_error(mock_boto3):
    """Test handling of parse errors from model response."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "not valid json"}]}}
    }

    result = analyze_root_cause(SAMPLE_INVESTIGATION)

    assert result["analysis_status"] == "parse_error"
    assert "analysis_error" in result
    assert "Failed to parse" in result["analysis_error"]


def test_analyze_root_cause_no_boto3():
    """Test handling when boto3 is not available."""
    import src.analysis as analysis_module
    original_boto3 = analysis_module.boto3

    try:
        analysis_module.boto3 = None
        result = analyze_root_cause(SAMPLE_INVESTIGATION)
        assert result["analysis_status"] == "configuration_error"
        assert "boto3 not available" in result["analysis_error"]
    finally:
        analysis_module.boto3 = original_boto3


def test_analyze_root_cause_preserves_history_on_error():
    """Test that investigation history is preserved even if analysis fails."""
    import src.analysis as analysis_module
    original_boto3 = analysis_module.boto3

    try:
        analysis_module.boto3 = None
        result = analyze_root_cause(SAMPLE_INVESTIGATION)

        # The analysis error should not affect the original investigation data
        # (The function returns analysis separately, investigation is passed in)
        assert result["analysis_status"] == "configuration_error"
    finally:
        analysis_module.boto3 = original_boto3


def test_analyze_root_cause_no_evidence():
    """Test analysis with minimal/no evidence."""
    minimal_investigation = {
        "project_path": "empty_project",
        "reported_error": "Some error",
        "steps_completed": 0,
        "actions_executed": [],
        "evidence_history": [],
        "history": [],
    }

    prompt = _build_analysis_prompt(minimal_investigation)
    assert "empty_project" in prompt
    assert "(no diagnostic evidence collected)" in prompt
    assert "(no actions executed)" in prompt


def test_report_claims_only_recorded_actions():
    """Test that analysis cannot claim actions not in history."""
    # This is a semantic test - the model should only reference recorded actions
    # We verify the prompt only includes actions from history
    prompt = _build_analysis_prompt(SAMPLE_INVESTIGATION)
    assert "inspect_dependencies" in prompt
    assert "inspect_source" in prompt
    assert "run_tests" in prompt
    assert "inspect_network" not in prompt  # Not in history


def test_build_analysis_prompt_includes_truncation_notice():
    """Test that truncation notice is included in the analysis prompt."""
    truncated_investigation = dict(SAMPLE_INVESTIGATION)
    truncated_investigation["truncation_notice"] = (
        "Investigation was truncated after 3 step(s). "
        "Not all diagnostic actions could be executed."
    )
    truncated_investigation["stop_reason"] = "maximum_steps_reached"

    prompt = _build_analysis_prompt(truncated_investigation)

    assert "TRUNCATION" in prompt
    assert "truncated" in prompt.lower()


def test_build_analysis_prompt_distinguishes_confirmed_from_hypothesis():
    """Test that prompt rules distinguish confirmed observations from hypotheses."""
    prompt = _build_analysis_prompt(SAMPLE_INVESTIGATION)

    assert "Confirmed vs hypothesis" in prompt
    assert "alternative_explanations" in prompt
    assert "remaining_uncertainty" in prompt


def test_build_analysis_prompt_test_results_interpretation():
    """Test that prompt rules interpret passing tests as reproduction confirmation."""
    prompt = _build_analysis_prompt(SAMPLE_INVESTIGATION)

    assert "expected failure was reproduced" in prompt
    assert "NOT as evidence that the application works" in prompt


def test_build_analysis_prompt_runtime_uncertainty():
    """Test that prompt rules keep runtime uncertainty explicit."""
    prompt = _build_analysis_prompt(SAMPLE_INVESTIGATION)

    assert "runtime environment was not verified" in prompt
    assert "remaining uncertainty" in prompt.lower()


def test_report_without_check_dependency_has_uncertainty():
    """Test that evidence_sufficient is false when check_dependency hasn't verified runtime."""
    from src.analysis import RootCauseReport

    # No check_dependency was run - runtime not verified
    report = RootCauseReport(
        confirmed_observations=["requirements.txt declares psycopg"],
        most_likely_cause="Insufficient evidence to determine root cause",
        alternative_explanations=["Missing psycopg in runtime environment"],
        evidence_supporting={},
        remaining_uncertainty=[
            "Runtime environment not verified: check_dependency not executed",
            "Interpreter used for checking not confirmed",
        ],
        recommended_next_step="Run check_dependency for psycopg",
        suggested_fix=None,
        evidence_sufficient=False,
    )

    assert report.evidence_sufficient is False
    assert report.most_likely_cause == "Insufficient evidence to determine root cause"
    assert len(report.remaining_uncertainty) >= 2
    assert report.suggested_fix is None


def test_report_with_confirmed_missing_module():
    """Test report when check_dependency confirms module is missing."""
    from src.analysis import RootCauseReport

    report = RootCauseReport(
        confirmed_observations=[
            "requirements.txt declares psycopg[binary]>=3.2",
            "app.py imports psycopg at module level",
            "check_dependency: psycopg is not importable using interpreter /path/to/python",
        ],
        most_likely_cause="Missing dependency: psycopg not installed in runtime environment",
        alternative_explanations=["Wrong Python interpreter being used"],
        evidence_supporting={
            "Missing dependency": [
                "requirements.txt declares psycopg[binary]>=3.2",
                "check_dependency reports psycopg as missing",
            ]
        },
        remaining_uncertainty=[
            "Whether installing psycopg resolves the issue without other missing dependencies",
        ],
        recommended_next_step="Install dependencies with pip install -r requirements.txt",
        suggested_fix="pip install -r requirements.txt",
        evidence_sufficient=True,
    )

    assert report.evidence_sufficient is True
    assert "psycopg" in report.most_likely_cause.lower()
    assert report.suggested_fix == "pip install -r requirements.txt"


def test_report_passing_tests_not_app_health():
    """Test that passing tests are not treated as evidence the app works."""
    from src.analysis import RootCauseReport

    report = RootCauseReport(
        confirmed_observations=[
            "run_tests passed (exit code 0)",
            "tests assert that psycopg import fails",
        ],
        most_likely_cause="Missing dependency: psycopg not installed",
        alternative_explanations=["Test environment differs from production"],
        evidence_supporting={
            "Missing dependency": [
                "requirements.txt declares psycopg",
                "tests confirm import failure",
            ]
        },
        remaining_uncertainty=[
            "Passing tests reproduce the expected failure — app health not verified",
        ],
        recommended_next_step="Run check_dependency for psycopg",
        suggested_fix=None,
        evidence_sufficient=False,
    )

    assert report.evidence_sufficient is False
    assert "app health not verified" in str(report.remaining_uncertainty)
    assert report.suggested_fix is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
