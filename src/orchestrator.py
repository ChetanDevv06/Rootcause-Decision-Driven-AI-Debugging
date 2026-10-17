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
from src.diagnostics import (
    inspect_dependencies,
    inspect_source,
    run_tests,
    check_dependency,
    _extract_module_from_error,
    MODULE_NAME_PATTERN,
)
from src.analysis import analyze_root_cause


MAX_STEPS = 3
MAX_STEPS_LIMIT = 10  # Hard upper bound


def execute_action(
    action: str,
    config: TargetProjectConfig,
    arguments: dict[str, Any] | None = None,
    error: str | None = None,
    evidence_history: list[str] | None = None,
) -> dict[str, Any]:
    """Execute only a recognized diagnostic action."""
    arguments = arguments or {}
    evidence_history = evidence_history or []

    if action == "inspect_dependencies":
        return inspect_dependencies(config)

    if action == "inspect_source":
        return inspect_source(config)

    if action == "run_tests":
        return run_tests(config)

    if action == "check_dependency":
        # Derive the module name from trusted investigation context, never
        # from arguments supplied by the Decider (which may be empty or
        # attacker-controlled).
        module_name = _derive_module_name(error, evidence_history)
        if not module_name:
            return {
                "action": "check_dependency",
                "project_path": str(config.root),
                "module": "",
                "command": None,
                "exit_code": None,
                "status": "insufficient_context",
                "stdout": "",
                "stderr": (
                    "Cannot check dependency: no module name could be derived "
                    "from the reported error or verified evidence."
                ),
                "timeout": config.test_timeout,
                "evidence": (
                    "Insufficient context: check_dependency requires a module "
                    "name, but none could be derived from the reported error "
                    "or verified evidence. Provide the module name explicitly."
                ),
            }
        return check_dependency(config, module_name)

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


def _derive_module_name(
    error: str | None,
    evidence_history: list[str],
) -> str:
    """Derive a module name from trusted investigation context.

    Preference order:
    1. Parse the module name from a reported ModuleNotFoundError.
    2. Scan verified evidence for a module name (e.g. import statements or
       dependency declarations already confirmed by diagnostics).
    3. Return an empty string if the module remains ambiguous.
    """
    if error:
        candidate = _extract_module_from_error(error)
        if candidate and MODULE_NAME_PATTERN.match(candidate):
            return candidate

    # Fall back to verified evidence only when the error did not yield a
    # usable name. Avoid accepting anything the Decider may have supplied.
    for entry in evidence_history:
        candidate = _extract_module_from_error(entry)
        if candidate and MODULE_NAME_PATTERN.match(candidate):
            return candidate

    return ""


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
        "check_dependency": (
            "Check whether a specific Python module is importable using the "
            "project's interpreter. Does not install packages or modify files."
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

        arguments = decision.get("arguments", {}) or {}
        result = execute_action(
            selected,
            config,
            arguments=arguments,
            error=error,
            evidence_history=evidence_history,
        )
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

        # Stop only on genuine diagnostic-tool failures (error/timeout) that
        # prevent progress. Do not stop on legitimate findings (installed,
        # missing, insufficient_context) — those are evidence for the Decider.
        result_status = result.get("status", "")
        if result_status in ("error", "timeout"):
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

    # When the step budget is exhausted, add a clear truncation notice so
    # the final report does not misrepresent incomplete evidence as sufficient.
    if investigation["stop_reason"] == "maximum_steps_reached":
        investigation["truncation_notice"] = (
            f"Investigation was truncated after {max_steps} step(s). "
            "Not all diagnostic actions could be executed; the final report "
            "reflects only the evidence collected before truncation."
        )

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