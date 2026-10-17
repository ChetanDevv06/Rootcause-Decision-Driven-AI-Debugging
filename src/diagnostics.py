from pathlib import Path
from typing import Final
import subprocess
import os

from src.config import (
    EXCLUDED_DIRS,
    EXCLUDED_FILES,
    TargetProjectConfig,
)
from src.analysis import _redact_dict

DEPENDENCY_FILES: Final[tuple[str, ...]] = (
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
)


def _should_exclude_path(path: Path, root: Path) -> bool:
    """Check if a path should be excluded from inspection."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True

    if path.name in EXCLUDED_FILES:
        return True

    if path.name.startswith(".env"):
        return True

    if path.suffix in {".pem", ".key", ".p12", ".pfx", ".crt", ".cer"}:
        return True

    return False


def inspect_dependencies(config: TargetProjectConfig) -> dict:
    """Read common Python dependency files without modifying them."""
    root = config.root

    found = {}

    for filename in DEPENDENCY_FILES:
        file_path = root / filename

        # Explicit safety check: ensure path is within root
        try:
            file_path.relative_to(root)
        except ValueError:
            continue

        if _should_exclude_path(file_path, root):
            continue

        if file_path.is_file():
            try:
                found[filename] = file_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )[: config.max_dep_chars]
            except OSError as exc:
                found[filename] = f"Could not read file: {exc}"

    return {
        "action": "inspect_dependencies",
        "project_path": str(root),
        "files_found": found,
        "evidence": (
            "Dependency files were inspected."
            if found
            else "No supported dependency files were found."
        ),
    }


def inspect_source(config: TargetProjectConfig) -> dict:
    """Read a limited number of Python files as diagnostic evidence."""
    root = config.root

    files: dict[str, str] = {}

    for path in root.rglob("*.py"):
        # Explicit safety check: ensure path is within root
        try:
            path.relative_to(root)
        except ValueError:
            continue

        if _should_exclude_path(path, root):
            continue

        try:
            relative = str(path.relative_to(root))
            files[relative] = path.read_text(
                encoding="utf-8",
                errors="replace",
            )[: config.max_chars_per_file]
        except OSError:
            continue

        if len(files) >= config.max_files:
            break

    return {
        "action": "inspect_source",
        "project_path": str(root),
        "files_found": files,
        "evidence": f"Read {len(files)} Python source files.",
    }


SAFE_ENV_KEYS = {
    "PATH",
    "HOME",
    "USER",
    "USERNAME",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "PYTHONPATH",
    "PYTHONHOME",
    "VIRTUAL_ENV",
    "CONDA_DEFAULT_ENV",
    "CONDA_PREFIX",
}

# Keys to explicitly drop from the environment for safety
UNSAFE_ENV_KEYS = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_DEFAULT_REGION",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "NPM_TOKEN",
    "PYPI_TOKEN",
    "DATABASE_URL",
    "DATABASE_PASSWORD",
    "SECRET_KEY",
    "API_KEY",
    "PRIVATE_KEY",
    "SSH_PRIVATE_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_CLIENT_SECRET",
}


def _filter_environment() -> dict[str, str]:
    """Create a filtered environment for subprocess execution."""
    env = os.environ.copy()
    # Keep only safe keys, drop unsafe ones
    filtered = {k: v for k, v in env.items() if k in SAFE_ENV_KEYS or k not in UNSAFE_ENV_KEYS}
    # Ensure we don't accidentally leak secrets
    return filtered


def run_tests(config: TargetProjectConfig) -> dict:
    """Execute the configured test command in the target project directory.

    This diagnostic runs a predefined test command (default: pytest) against
    the target project. It captures stdout, stderr, and the exit code with
    strict limits on output size and execution time.

    Safety notes:
    - Only the configured test command is executed; no arbitrary shell commands.
    - The working directory is restricted to the validated target project path.
    - Environment is filtered to remove known sensitive variables.
    - Test execution is a read-only diagnostic; it does not install dependencies
      or modify the target project.
    - Tests are executable code and should only be run on trusted projects
      or inside a properly isolated environment.
    - A failed test does not prove a unique root cause; it only provides
      additional evidence for the Decider to consider.
    """
    root = config.root

    # Build the command as a list (no shell=True)
    cmd = list(config.test_command)

    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=config.test_timeout,
            env=_filter_environment(),
        )

        stdout = result.stdout[: config.max_test_output]
        stderr = result.stderr[: config.max_test_output]

        # Redact secrets from test output
        stdout = _redact_dict(stdout)
        stderr = _redact_dict(stderr)

        if result.returncode == 0:
            status = "passed"
            evidence = f"Tests passed (exit code 0)."
        else:
            status = "failed"
            evidence = f"Tests failed with exit code {result.returncode}."

        return {
            "action": "run_tests",
            "project_path": str(root),
            "command": cmd,
            "exit_code": result.returncode,
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "timeout": config.test_timeout,
            "evidence": evidence,
        }

    except subprocess.TimeoutExpired:
        return {
            "action": "run_tests",
            "project_path": str(root),
            "command": cmd,
            "exit_code": None,
            "status": "timeout",
            "stdout": "",
            "stderr": f"Test execution timed out after {config.test_timeout} seconds.",
            "timeout": config.test_timeout,
            "evidence": f"Tests timed out after {config.test_timeout} seconds.",
        }

    except FileNotFoundError:
        return {
            "action": "run_tests",
            "project_path": str(root),
            "command": cmd,
            "exit_code": None,
            "status": "error",
            "stdout": "",
            "stderr": f"Test runner not found: {cmd[0]}. Ensure the test command is available.",
            "timeout": config.test_timeout,
            "evidence": f"Test runner not found: {cmd[0]}.",
        }

    except OSError as exc:
        return {
            "action": "run_tests",
            "project_path": str(root),
            "command": cmd,
            "exit_code": None,
            "status": "error",
            "stdout": "",
            "stderr": f"Execution error: {exc}",
            "timeout": config.test_timeout,
            "evidence": f"Failed to execute tests: {exc}",
        }