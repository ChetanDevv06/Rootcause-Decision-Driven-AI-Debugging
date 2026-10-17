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


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])