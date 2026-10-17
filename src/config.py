from pathlib import Path
import sys
from typing import Final

EXCLUDED_DIRS: Final[set[str]] = {
    ".git",
    ".venv",
    ".venv314",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".eggs",
    "htmlcov",
    ".coverage",
}

EXCLUDED_FILES: Final[set[str]] = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "id_dsa",
    "id_ecdsa",
    "private_key.pem",
    "private_key.ppk",
    "aws_credentials",
    "credentials",
    "service_account.json",
    "gcp_credentials.json",
    "firebase_admin_sdk.json",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "secrets.yaml",
    "secrets.yml",
    "vault.yml",
    "vault.yaml",
}

DEFAULT_MAX_FILES: Final[int] = 10
DEFAULT_MAX_CHARS_PER_FILE: Final[int] = 4000
DEFAULT_MAX_DEP_CHARS: Final[int] = 12000

DEFAULT_TEST_COMMAND: Final[list[str]] = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
DEFAULT_TEST_TIMEOUT: Final[int] = 60
DEFAULT_MAX_TEST_OUTPUT: Final[int] = 8000


class TargetProjectConfig:
    def __init__(
        self,
        project_path: str,
        max_files: int = DEFAULT_MAX_FILES,
        max_chars_per_file: int = DEFAULT_MAX_CHARS_PER_FILE,
        max_dep_chars: int = DEFAULT_MAX_DEP_CHARS,
        test_command: list[str] | None = None,
        test_timeout: int = DEFAULT_TEST_TIMEOUT,
        max_test_output: int = DEFAULT_MAX_TEST_OUTPUT,
    ) -> None:
        self.project_path = self._validate_path(project_path)
        self.max_files = max_files
        self.max_chars_per_file = max_chars_per_file
        self.max_dep_chars = max_dep_chars
        self.test_command = test_command or DEFAULT_TEST_COMMAND
        self.test_timeout = test_timeout
        self.max_test_output = max_test_output

    def _validate_path(self, path: str) -> Path:
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise ValueError(f"Target project path does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"Target project path is not a directory: {resolved}")
        return resolved

    @property
    def root(self) -> Path:
        return self.project_path

    def __repr__(self) -> str:
        return (
            f"TargetProjectConfig(project_path={self.project_path!r}, "
            f"max_files={self.max_files}, max_chars_per_file={self.max_chars_per_file}, "
            f"test_command={self.test_command}, test_timeout={self.test_timeout})"
        )


def create_config_from_args(args: list[str] | None = None) -> TargetProjectConfig:
    import argparse
    import shlex

    parser = argparse.ArgumentParser(
        description="Rootcause - Decision-first AI debugging agent",
        add_help=True,
    )
    parser.add_argument(
        "--project-path",
        type=str,
        default=".",
        help="Path to the target project to investigate (default: current directory)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"Maximum number of source files to read (default: {DEFAULT_MAX_FILES})",
    )
    parser.add_argument(
        "--max-chars-per-file",
        type=int,
        default=DEFAULT_MAX_CHARS_PER_FILE,
        help=f"Maximum characters per source file (default: {DEFAULT_MAX_CHARS_PER_FILE})",
    )
    parser.add_argument(
        "--max-dep-chars",
        type=int,
        default=DEFAULT_MAX_DEP_CHARS,
        help=f"Maximum characters per dependency file (default: {DEFAULT_MAX_DEP_CHARS})",
    )
    parser.add_argument(
        "--test-command",
        type=str,
        default=None,
        help=f"Test command to run (default: {' '.join(DEFAULT_TEST_COMMAND)})",
    )
    parser.add_argument(
        "--test-timeout",
        type=int,
        default=DEFAULT_TEST_TIMEOUT,
        help=f"Test execution timeout in seconds (default: {DEFAULT_TEST_TIMEOUT})",
    )
    parser.add_argument(
        "--max-test-output",
        type=int,
        default=DEFAULT_MAX_TEST_OUTPUT,
        help=f"Maximum test output characters to capture (default: {DEFAULT_MAX_TEST_OUTPUT})",
    )

    parsed = parser.parse_args(args)

    # Parse test command string into list without breaking paths containing spaces.
    if parsed.test_command is None:
        test_cmd = list(DEFAULT_TEST_COMMAND)
    else:
        test_cmd = shlex.split(parsed.test_command) if parsed.test_command else list(DEFAULT_TEST_COMMAND)

    return TargetProjectConfig(
        project_path=parsed.project_path,
        max_files=parsed.max_files,
        max_chars_per_file=parsed.max_chars_per_file,
        max_dep_chars=parsed.max_dep_chars,
        test_command=test_cmd,
        test_timeout=parsed.test_timeout,
        max_test_output=parsed.max_test_output,
    )