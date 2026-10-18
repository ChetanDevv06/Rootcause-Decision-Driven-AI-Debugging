"""Rootcause web API — FastAPI backend for the diagnostic engine.

Exposes two endpoints:
  GET    /api/health        — API and dependency/service status
  POST   /api/investigations — start an investigation and return real results

The backend calls the existing orchestrator (`src/orchestrator.investigate`)
directly. No investigation logic is duplicated and no results are fabricated.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Final, Any

from src.config import TargetProjectConfig
from src.orchestrator import investigate, MAX_STEPS_LIMIT
from src.demo_scenarios import (
    DemoScenario,
    ExpectedOutcome,
    fixture_absolute_path,
    expected_outcomes,
    get_scenario,
    list_scenarios,
)

# Resolve the repository root (parent of the `src` package) for fixture paths.
REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Rootcause API",
    description="Evidence-first debugging API for the Rootcause diagnostic engine.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class InvestigationRequest(BaseModel):
    """Request body for starting an investigation."""

    project_path: str = Field(
        ...,
        description="Absolute or relative path to the target project directory.",
    )
    error: str = Field(
        ...,
        min_length=1,
        description="The reported error message or stack trace to investigate.",
    )
    max_steps: int | None = Field(
        default=None,
        ge=1,
        le=MAX_STEPS_LIMIT,
        description=f"Maximum diagnostic steps (1-{MAX_STEPS_LIMIT}). Defaults to orchestrator default.",
    )


class InvestigationResponse(BaseModel):
    """Response body containing the real investigation result."""

    project_path: str
    reported_error: str
    steps_completed: int
    actions_executed: list[str]
    evidence_history: list[str]
    history: list[dict[str, Any]]
    stop_reason: str
    truncation_notice: str | None = None
    analysis: dict[str, Any] | None = None
    analysis_status: str | None = None
    analysis_error: str | None = None


# ---------------------------------------------------------------------------
# Demo scenario models
# ---------------------------------------------------------------------------


class ExpectedOutcomeResponse(BaseModel):
    """Machine-readable expected outcome for a demo scenario."""

    scenario_id: str
    failure_category: str
    expected_evidence: list[str]
    expected_diagnosis_category: str
    suggested_corrective_action: str
    supported: bool
    limitations: list[str]


class ScenarioResponse(BaseModel):
    """A single demo scenario with its inputs and expected outcome."""

    id: str
    name: str
    category: str
    description: str
    fixture_dir: str
    project_path: str
    error: str
    expected_outcome: ExpectedOutcomeResponse


class ScenarioListResponse(BaseModel):
    """List of all available demo scenarios."""

    scenarios: list[ScenarioResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health", response_model=dict[str, Any])
def health() -> dict[str, Any]:
    """Report API status and dependency/service availability.

    Never exposes secrets, credentials, or private local paths.
    """
    # Check whether key modules are importable
    modules: dict[str, bool] = {}
    for name in ("fastapi", "uvicorn", "src.orchestrator", "src.analysis", "src.decider_client", "boto3"):
        try:
            importlib.import_module(name)
            modules[name] = True
        except ImportError:
            modules[name] = False

    # Check whether the Decider endpoint is reachable (best-effort, non-blocking)
    decider_reachable = False
    try:
        from urllib.request import Request, urlopen
        from urllib.error import URLError, HTTPError
        import json as _json

        req = Request("http://127.0.0.1:8099/health", method="GET")
        try:
            with urlopen(req, timeout=2) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    data = _json.loads(body)
                    decider_reachable = isinstance(data, dict) and data.get("status") == "ok"
                except _json.JSONDecodeError:
                    decider_reachable = False
        except (URLError, HTTPError, OSError):
            decider_reachable = False
    except Exception:  # pragma: no cover - defensive
        decider_reachable = False

    return {
        "status": "ok",
        "service": "rootcause",
        "version": "1.0.0",
        "modules": modules,
        "decider_reachable": decider_reachable,
        "bedrock_configured": modules.get("boto3", False),
    }


@app.get("/api/demo-scenarios", response_model=ScenarioListResponse)
def list_demo_scenarios() -> ScenarioListResponse:
    """Return all available demo scenarios with their inputs and fixture paths.

    Each scenario includes the absolute project path (resolved from the repo
    root) and the error text that reproduces the failure. The frontend uses
    this to populate the investigation form without starting an investigation.
    """
    scenarios = []
    for scenario in list_scenarios():
        project_path = str(fixture_absolute_path(scenario, REPO_ROOT))
        outcome = scenario.expected_outcome
        scenarios.append(
            ScenarioResponse(
                id=scenario.id,
                name=scenario.name,
                category=scenario.category,
                description=scenario.description,
                fixture_dir=scenario.fixture_dir,
                project_path=project_path,
                error=scenario.error,
                expected_outcome=ExpectedOutcomeResponse(
                    scenario_id=outcome.scenario_id,
                    failure_category=outcome.failure_category,
                    expected_evidence=outcome.expected_evidence,
                    expected_diagnosis_category=outcome.expected_diagnosis_category,
                    suggested_corrective_action=outcome.suggested_corrective_action,
                    supported=outcome.supported,
                    limitations=outcome.limitations,
                ),
            )
        )
    return ScenarioListResponse(scenarios=scenarios)


@app.get("/api/demo-scenarios/{scenario_id}", response_model=ScenarioResponse)
def get_demo_scenario(scenario_id: str) -> ScenarioResponse:
    """Return a single demo scenario by id."""
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Unknown demo scenario: {scenario_id}")
    project_path = str(fixture_absolute_path(scenario, REPO_ROOT))
    outcome = scenario.expected_outcome
    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        category=scenario.category,
        description=scenario.description,
        fixture_dir=scenario.fixture_dir,
        project_path=project_path,
        error=scenario.error,
        expected_outcome=ExpectedOutcomeResponse(
            scenario_id=outcome.scenario_id,
            failure_category=outcome.failure_category,
            expected_evidence=outcome.expected_evidence,
            expected_diagnosis_category=outcome.expected_diagnosis_category,
            suggested_corrective_action=outcome.suggested_corrective_action,
            supported=outcome.supported,
            limitations=outcome.limitations,
        ),
    )


@app.post("/api/investigations", response_model=InvestigationResponse)
def run_investigation(request: InvestigationRequest) -> InvestigationResponse:
    """Start a diagnostic investigation and return the real engine result.

    The investigation runs synchronously. The orchestrator handles Decider
    selection, diagnostic execution, and Bedrock-backed analysis. Unavailable
    external services (Decider, Bedrock) are handled gracefully by the
    orchestrator and reflected in the response.
    """
    try:
        config = TargetProjectConfig(
            project_path=request.project_path,
            max_files=10,
            max_chars_per_file=4000,
            max_dep_chars=12000,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    max_steps = request.max_steps

    try:
        result = investigate(
            config=config,
            error=request.error,
            evidence=None,
            max_steps=max_steps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Investigation failed: {exc}")

    return InvestigationResponse(
        project_path=result.get("project_path", request.project_path),
        reported_error=result.get("reported_error", request.error),
        steps_completed=result.get("steps_completed", 0),
        actions_executed=result.get("actions_executed", []),
        evidence_history=result.get("evidence_history", []),
        history=result.get("history", []),
        stop_reason=result.get("stop_reason", "unknown"),
        truncation_notice=result.get("truncation_notice"),
        analysis=_unwrap_analysis(result.get("analysis")),
        analysis_status=_get_analysis_status(result.get("analysis")),
        analysis_error=_get_analysis_error(result.get("analysis")),
    )


def _unwrap_analysis(analysis: Any) -> dict[str, Any] | None:
    """Extract the report dict from the orchestrator's analysis wrapper.

    The orchestrator returns {"analysis": {...report...}, "analysis_status": "..."}
    on success, or {"analysis_error": "...", "analysis_status": "..."} on failure.
    We always return a dict so the frontend never renders ``undefined``.
    """
    if not isinstance(analysis, dict):
        return _empty_analysis("not_available", None)
    inner = analysis.get("analysis")
    if isinstance(inner, dict):
        return inner
    # Analysis failed or was not produced — return a minimal, non-fabricated
    # object so the frontend can render an honest status instead of undefined.
    return _empty_analysis(
        analysis.get("analysis_status") or "error",
        analysis.get("analysis_error"),
    )


def _empty_analysis(status: str, error: str | None) -> dict[str, Any]:
    """Return a minimal analysis object with no fabricated findings."""
    return {
        "most_likely_cause": None,
        "confirmed_observations": [],
        "alternative_explanations": [],
        "evidence_supporting": {},
        "remaining_uncertainty": [],
        "recommended_next_step": None,
        "suggested_fix": None,
        "evidence_sufficient": False,
        "_analysis_status": status,
        "_analysis_error": error,
    }


def _get_analysis_status(analysis: Any) -> str | None:
    if isinstance(analysis, dict):
        return analysis.get("analysis_status")
    return None


def _get_analysis_error(analysis: Any) -> str | None:
    if isinstance(analysis, dict):
        return analysis.get("analysis_error")
    return None
