
from pathlib import Path
from typing import Any

from src.decider_client import choose_next_action
from src.diagnostics import inspect_dependencies


MAX_STEPS = 3

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".venv314",
    "__pycache__",
    "node_modules",
}


def inspect_source(project_path: str) -> dict[str, Any]:
    """Read a limited number of Python files as diagnostic evidence."""
    root = Path(project_path).resolve()

    if not root.is_dir():
        return {
            "action": "inspect_source",
            "error": "Project path is not a directory.",
        }

    files: dict[str, str] = {}

    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        try:
            relative = str(path.relative_to(root))
            files[relative] = path.read_text(
                encoding="utf-8",
                errors="replace",
            )[:4000]
        except OSError:
            continue

        if len(files) >= 10:
            break

    return {
        "action": "inspect_source",
        "project_path": str(root),
        "files_found": files,
        "evidence": f"Read {len(files)} Python source files.",
    }


def execute_action(action: str, project_path: str) -> dict[str, Any]:
    """Execute only a recognized diagnostic action."""
    if action == "inspect_dependencies":
        return inspect_dependencies(project_path)

    if action == "inspect_source":
        return inspect_source(project_path)

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
    project_path: str,
    error: str,
    evidence: list[str] | None = None,
    max_steps: int = MAX_STEPS,
) -> dict[str, Any]:
    """Run a bounded, evidence-driven diagnostic investigation."""
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1.")

    root = Path(project_path).resolve()

    if not root.is_dir():
        raise ValueError(f"Project path is not a directory: {root}")

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

        decision = choose_next_action(
            error=error,
            evidence=evidence_history,
            available_actions=available_actions,
        )

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

        result = execute_action(selected, str(root))
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

    return {
        "project_path": str(root),
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


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent

    result = investigate(
        project_path=str(project_root),
        error="ModuleNotFoundError: No module named 'psycopg'",
        evidence=[
            "The application reports a missing psycopg module.",
            "The dependency manifest has not yet been inspected.",
        ],
    )

    import json

    print("\n=== Rootcause investigation ===")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
