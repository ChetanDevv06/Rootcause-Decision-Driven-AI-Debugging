from pathlib import Path
from typing import Any

from src.config import TargetProjectConfig, create_config_from_args
from src.decider_client import (
    choose_next_action,
    DeciderError,
    DeciderConnectionError,
    DeciderTimeoutError,
    DeciderHTTPError,
    DeciderInvalidResponseError,
    DeciderValidationError,
)
from src.diagnostics import inspect_dependencies, inspect_source, run_tests
from src.analysis import analyze_root_cause


MAX_STEPS = 3
MAX_STEPS_LIMIT = 10  # Hard upper bound


def execute_action(action: str, config: TargetProjectConfig) -> dict[str, Any]:
    """Execute only a recognized diagnostic action."""
    if action == "inspect_dependencies":
        return inspect_dependencies(config)

    if action == "inspect_source":
        return inspect_source(config)

    if action == "run_tests":
        return run_tests(config)

    if action == "stop_and_report":
        return {
            "action": "stop_and_report",
            "evidence": "Decider requested that the investigation stop.",
        }

    # Fail closed if an unexpected action reaches the executor.
    raise ValueError(f"Unsupported diagnostic action: {action}")


def summarize_result(result: dict[str, Any]) -> str:
    """Create a compact representation for the next decision."""
    import json

    return json.dumps(result, ensure_ascii=False, default=str)[:6000]


def investigate(
    config: TargetProjectConfig,
    error: str,
    evidence: list[str] | None = None,
    max_steps: int = MAX_STEPS,
) -> dict[str, Any]:
    """Run a bounded, evidence-driven diagnostic investigation."""
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1.")
    if max_steps > MAX_STEPS_LIMIT:
        raise ValueError(f"max_steps cannot exceed {MAX_STEPS_LIMIT}")

    evidence_history = list(evidence or [])
    executed_actions: list[str] = []
    history: list[dict[str, Any]] = []

    action_descriptions = {
        "inspect_dependencies": (
            "Inspect dependency manifests for declarations "
            "relevant to the reported error."
        ),
        "inspect_source": (
            "Inspect Python source files for imports or code "
            "relevant to the reported error."
        ),
        "run_tests": (
            "Execute the project's test suite to gather runtime evidence. "
            "Runs a predefined test command (default: pytest) with timeout "
            "and output limits. Does not install dependencies or modify files."
        ),
        "stop_and_report": (
            "Stop collecting evidence and report what is currently known."
        ),
    }

    for step in range(1, max_steps + 1):
        # Each diagnostic runs at most once per investigation.
        available_actions = {
            name: description
            for name, description in action_descriptions.items()
            if name == "stop_and_report" or name not in executed_actions
        }

        try:
            decision = choose_next_action(
                error=error,
                evidence=evidence_history,
                available_actions=available_actions,
            )
        except (DeciderConnectionError, DeciderTimeoutError, DeciderHTTPError,
                DeciderInvalidResponseError, DeciderValidationError) as exc:
            # Record the Decider error in history and stop gracefully
            history.append({
                "step": step,
                "decision_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
                "result": {
                    "action": "decider_error",
                    "evidence": f"Decider error: {exc}",
                },
            })
            break

        selected = decision["action"]

        if selected == "stop_and_report":
            history.append({
                "step": step,
                "decision": decision,
                "result": {
                    "action": "stop_and_report",
                    "evidence": "Investigation stopped by Decider.",
                },
            })
            break

        result = execute_action(selected, config)
        executed_actions.append(selected)

        history.append({
            "step": step,
            "decision": decision,
            "result": result,
        })

        # Feed the actual diagnostic output into the next decision.
        evidence_history.append(
            f"Step {step}: {selected} returned: "
            f"{summarize_result(result)}"
        )

        # Stop on diagnostic errors instead of treating them as evidence
        # that the original application has a particular root cause.
        if "error" in result:
            break

        if len(executed_actions) >= len(action_descriptions) - 1:
            # All available evidence-gathering actions have run.
            break

    investigation = {
        "project_path": str(config.root),
        "reported_error": error,
        "steps_completed": len(history),
        "actions_executed": executed_actions,
        "evidence_history": evidence_history,
        "history": history,
        "stop_reason": (
            "maximum_steps_reached"
            if len(history) >= max_steps
            else "investigation_finished"
        ),
    }

    # Generate final root-cause analysis using Bedrock
    analysis = analyze_root_cause(investigation)
    investigation["analysis"] = analysis

    return investigation


def main(args: list[str] | None = None) -> None:
    """CLI entry point for Rootcause investigation."""
    import json
    import argparse

    parser = argparse.ArgumentParser(
        description="Rootcause - Decision-first AI debugging agent",
        add_help=True,
    )
    # Add max_steps argument
    parser.add_argument(
        "--max-steps",
        type=int,
        default=MAX_STEPS,
        help=f"Maximum decision cycles (default: {MAX_STEPS}, max: {MAX_STEPS_LIMIT})",
    )
    # Parse only known args to allow passing through to config parser
    parsed, remaining = parser.parse_known_args(args)

    if parsed.max_steps < 1 or parsed.max_steps > MAX_STEPS_LIMIT:
        parser.error(f"max-steps must be between 1 and {MAX_STEPS_LIMIT}")

    config = create_config_from_args(remaining)

    # Default error and evidence for demonstration
    # In practice, these would come from CLI args or a config file
    error = "ModuleNotFoundError: No module named 'psycopg'"
    initial_evidence = [
        "The application reports a missing psycopg module.",
        "The dependency manifest has not yet been inspected.",
    ]

    result = investigate(
        config=config,
        error=error,
        evidence=initial_evidence,
        max_steps=parsed.max_steps,
    )

    print("\n=== Rootcause investigation ===")
    # Print investigation without analysis first (it's large)
    investigation_summary = {k: v for k, v in result.items() if k != "analysis"}
    print(json.dumps(investigation_summary, indent=2, ensure_ascii=True, default=str))

    # Print analysis separately
    analysis = result.get("analysis", {})
    print("\n=== Root-cause analysis ===")
    if analysis.get("analysis_status") == "success":
        print(json.dumps(analysis["analysis"], indent=2, ensure_ascii=True))
    else:
        print(json.dumps(analysis, indent=2, ensure_ascii=True, default=str))


if __name__ == "__main__":
    main()