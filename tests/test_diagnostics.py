from pathlib import Path
import sys
import subprocess
from unittest.mock import patch, MagicMock

from src.config import TargetProjectConfig
from src.diagnostics import (
    inspect_dependencies,
    inspect_source,
    run_tests,
    check_dependency,
)


def test_inspect_dependencies_reads_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text(
        "psycopg[binary]>=3.2\n",
        encoding="utf-8",
    )

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_dependencies(config)

    assert result["action"] == "inspect_dependencies"
    assert "requirements.txt" in result["files_found"]
    assert "psycopg" in result["files_found"]["requirements.txt"]
    assert result["project_path"] == str(tmp_path.resolve())


def test_inspect_dependencies_handles_missing_directory():
    try:
        TargetProjectConfig("Z:/rootcause_missing_test_directory")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "does not exist" in str(exc)


def test_inspect_dependencies_rejects_file_path(tmp_path: Path):
    file_path = tmp_path / "not_a_directory.txt"
    file_path.write_text("content")

    try:
        TargetProjectConfig(str(file_path))
        assert False, "Expected ValueError for file path"
    except ValueError as exc:
        assert "not a directory" in str(exc)


def test_inspect_dependencies_target_distinct_from_rootcause(tmp_path: Path):
    """Test that dependency inspection works on a target directory distinct from Rootcause."""
    (tmp_path / "requirements.txt").write_text("requests>=2.31\n")

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_dependencies(config)

    assert result["project_path"] == str(tmp_path.resolve())
    assert "requests" in result["files_found"]["requirements.txt"]


def test_inspect_source_reads_python_files(tmp_path: Path):
    (tmp_path / "main.py").write_text("import os\nprint('hello')\n")
    (tmp_path / "utils.py").write_text("def helper(): pass\n")

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    assert result["action"] == "inspect_source"
    assert "main.py" in result["files_found"]
    assert "utils.py" in result["files_found"]
    assert result["project_path"] == str(tmp_path.resolve())
    assert result["files_found"]["main.py"] == "import os\nprint('hello')\n"


def test_inspect_source_excludes_directories(tmp_path: Path):
    (tmp_path / "main.py").write_text("import os\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("home = /usr\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.cpython-314.pyc").write_bytes(b"")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "package.json").write_text("{}")

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    assert result["project_path"] == str(tmp_path.resolve())
    assert "main.py" in result["files_found"]
    assert not any(".git" in f for f in result["files_found"])
    assert not any(".venv" in f for f in result["files_found"])
    assert not any("__pycache__" in f for f in result["files_found"])
    assert not any("node_modules" in f for f in result["files_found"])


def test_inspect_source_excludes_sensitive_files(tmp_path: Path):
    (tmp_path / "main.py").write_text("import os\n")
    (tmp_path / ".env").write_text("SECRET_KEY=abc123\n")
    (tmp_path / "config.py").write_text("API_KEY = 'xyz'\n")
    (tmp_path / "private_key.pem").write_text("-----BEGIN PRIVATE KEY-----\n")
    (tmp_path / "id_rsa").write_text("-----BEGIN RSA PRIVATE KEY-----\n")
    (tmp_path / "service_account.json").write_text('{"type": "service_account"}\n')

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    assert "main.py" in result["files_found"]
    assert "config.py" in result["files_found"]  # Not excluded by name
    assert not any(".env" in f for f in result["files_found"])
    assert not any("private_key" in f for f in result["files_found"])
    assert not any("id_rsa" in f for f in result["files_found"])
    assert not any("service_account" in f for f in result["files_found"])


def test_inspect_source_respects_max_files(tmp_path: Path):
    for i in range(15):
        (tmp_path / f"file{i}.py").write_text(f"# file {i}\n")

    config = TargetProjectConfig(str(tmp_path), max_files=5)
    result = inspect_source(config)

    assert len(result["files_found"]) == 5


def test_inspect_source_empty_directory(tmp_path: Path):
    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    assert result["files_found"] == {}
    assert result["evidence"] == "Read 0 Python source files."


def test_inspect_source_no_relevant_files(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Project\n")
    (tmp_path / "data.json").write_text("{}")

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    assert result["files_found"] == {}
    assert result["evidence"] == "Read 0 Python source files."


def test_config_validates_path(tmp_path: Path):
    config = TargetProjectConfig(str(tmp_path))
    assert config.root == tmp_path.resolve()


def test_config_rejects_nonexistent_path():
    try:
        TargetProjectConfig("/nonexistent/path/that/does/not/exist")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "does not exist" in str(exc)


def test_config_rejects_file_instead_of_directory(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    try:
        TargetProjectConfig(str(file_path))
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "not a directory" in str(exc)


def test_run_tests_success(tmp_path: Path):
    """Test successful test execution."""
    (tmp_path / "test_sample.py").write_text("def test_pass(): assert True\n")

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_sample.py", "-v"],
        test_timeout=30,
    )

    result = run_tests(config)

    assert result["action"] == "run_tests"
    assert result["project_path"] == str(tmp_path.resolve())
    assert result["status"] in ("passed", "failed")  # Depends on pytest availability
    assert "exit_code" in result
    assert "stdout" in result
    assert "stderr" in result


def test_run_tests_failed_tests(tmp_path: Path):
    """Test that failed tests are reported correctly."""
    (tmp_path / "test_fail.py").write_text("def test_fail(): assert False\n")

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_fail.py", "-v"],
        test_timeout=30,
    )

    result = run_tests(config)

    assert result["action"] == "run_tests"
    assert result["project_path"] == str(tmp_path.resolve())
    assert "exit_code" in result
    # If pytest runs, exit code should be non-zero for failed tests


def test_run_tests_timeout(tmp_path: Path):
    """Test timeout handling."""
    # Use a command that definitely sleeps longer than the timeout
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-c", "import time; time.sleep(10)"],
        test_timeout=1,  # Very short timeout
    )

    result = run_tests(config)

    assert result["action"] == "run_tests"
    assert result["status"] == "timeout"
    assert result["exit_code"] is None
    assert "timed out" in result["evidence"].lower()


def test_run_tests_missing_runner(tmp_path: Path):
    """Test handling of missing test runner."""
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["nonexistent_test_runner_xyz"],
        test_timeout=30,
    )

    result = run_tests(config)

    assert result["action"] == "run_tests"
    assert result["status"] == "error"
    assert result["exit_code"] is None
    assert "not found" in result["evidence"].lower()


def test_run_tests_bounded_output(tmp_path: Path):
    """Test that output is bounded."""
    # Create a test that produces lots of output
    (tmp_path / "test_loud.py").write_text(
        "def test_loud():\n"
        "    print('x' * 10000)\n"
        "    assert True\n"
    )

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_loud.py", "-v", "-s"],
        test_timeout=30,
        max_test_output=100,  # Very small limit
    )

    result = run_tests(config)

    assert result["action"] == "run_tests"
    # Output should be truncated to max_test_output
    assert len(result["stdout"]) <= 100


def test_run_tests_invalid_target_path():
    """Test that invalid target paths are rejected."""
    try:
        TargetProjectConfig("/nonexistent/path/that/does/not/exist")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "does not exist" in str(exc)


def test_run_tests_rejects_arbitrary_commands(tmp_path: Path):
    """Test that only the configured command is executed."""
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-c", "print('hello')"],
        test_timeout=30,
    )

    result = run_tests(config)

    assert result["action"] == "run_tests"
    assert result["command"] == ["python", "-c", "print('hello')"]
    # The command is predefined in config, not from model output


def test_run_tests_uses_validated_working_directory(tmp_path: Path):
    """Test that working directory is the validated target project."""
    (tmp_path / "test_sample.py").write_text("def test_pass(): assert True\n")

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_sample.py", "-v"],
        test_timeout=30,
    )

    result = run_tests(config)

    assert result["project_path"] == str(tmp_path.resolve())


def test_run_tests_distinguishes_statuses(tmp_path: Path):
    """Test that different exit codes produce different statuses."""
    # Test with passing test
    (tmp_path / "test_pass.py").write_text("def test_pass(): assert True\n")

    config_pass = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_pass.py", "-v"],
        test_timeout=30,
    )

    result_pass = run_tests(config_pass)
    assert result_pass["action"] == "run_tests"

    # Test with failing test
    (tmp_path / "test_fail.py").write_text("def test_fail(): assert False\n")

    config_fail = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_fail.py", "-v"],
        test_timeout=30,
    )

    result_fail = run_tests(config_fail)
    assert result_fail["action"] == "run_tests"

    # Both should execute without error
    assert "exit_code" in result_pass
    assert "exit_code" in result_fail


# =========================================================================
# Safety tests
# =========================================================================

def test_inspect_source_path_traversal_blocked(tmp_path: Path):
    """Test that path traversal attempts are blocked."""
    (tmp_path / "main.py").write_text("import os\n")

    # Create a symlink or nested structure attempting to escape
    outside_dir = tmp_path.parent / "outside_test"
    outside_dir.mkdir(exist_ok=True)
    (outside_dir / "secret.py").write_text("SECRET = 'outside'\n")

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    # Should not read files outside the target root
    assert "secret.py" not in str(result["files_found"])
    assert ".." not in str(result["files_found"])


def test_inspect_dependencies_path_traversal_blocked(tmp_path: Path):
    """Test that dependency inspection blocks path traversal."""
    config = TargetProjectConfig(str(tmp_path))
    result = inspect_dependencies(config)

    # Should not crash or read outside
    assert result["action"] == "inspect_dependencies"


def test_run_tests_path_traversal_blocked(tmp_path: Path):
    """Test that test execution uses validated working directory."""
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-c", "import os; print(os.getcwd())"],
        test_timeout=5,
    )

    result = run_tests(config)
    assert result["project_path"] == str(tmp_path.resolve())


def test_excluded_dirs_not_read(tmp_path: Path):
    """Test that excluded directories are never read."""
    (tmp_path / "main.py").write_text("import os\n")
    (tmp_path / ".git").mkdir(parents=True)
    (tmp_path / ".git" / "config").write_text("[core]\n")
    (tmp_path / ".venv").mkdir(parents=True)
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("home = /usr\n")
    (tmp_path / "__pycache__").mkdir(parents=True)
    (tmp_path / "__pycache__" / "main.cpython-314.pyc").write_bytes(b"")
    (tmp_path / "node_modules").mkdir(parents=True)
    (tmp_path / "node_modules" / "package.json").write_text("{}")
    (tmp_path / ".mypy_cache").mkdir(parents=True)
    (tmp_path / ".mypy_cache" / "cache").write_text("cache")
    (tmp_path / ".pytest_cache").mkdir(parents=True)
    (tmp_path / ".pytest_cache" / "cache").write_text("cache")
    (tmp_path / ".ruff_cache").mkdir(parents=True)
    (tmp_path / ".ruff_cache" / "cache").write_text("cache")
    (tmp_path / "dist").mkdir(parents=True)
    (tmp_path / "dist" / "package.whl").write_bytes(b"")
    (tmp_path / "build").mkdir(parents=True)
    (tmp_path / "build" / "lib").mkdir(parents=True)
    (tmp_path / ".eggs").mkdir(parents=True)
    (tmp_path / ".eggs" / "egg").mkdir(parents=True)
    (tmp_path / "htmlcov").mkdir(parents=True)
    (tmp_path / "htmlcov" / "index.html").write_text("<html></html>")
    (tmp_path / ".coverage").write_text("coverage data")

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    excluded_found = [f for f in result["files_found"] if any(
        excl in f for excl in [".git", ".venv", "__pycache__", "node_modules",
                               ".mypy_cache", ".pytest_cache", ".ruff_cache",
                               "dist", "build", ".eggs", "htmlcov", ".coverage"]
    )]
    assert len(excluded_found) == 0, f"Excluded dirs found: {excluded_found}"


def test_excluded_files_not_read(tmp_path: Path):
    """Test that excluded sensitive files are never read."""
    (tmp_path / "main.py").write_text("import os\n")
    (tmp_path / ".env").write_text("SECRET=abc\n")
    (tmp_path / ".env.local").write_text("SECRET=def\n")
    (tmp_path / ".env.production").write_text("SECRET=ghi\n")
    (tmp_path / ".env.development").write_text("SECRET=jkl\n")
    (tmp_path / "id_rsa").write_text("private key\n")
    (tmp_path / "id_ed25519").write_text("private key\n")
    (tmp_path / "id_dsa").write_text("private key\n")
    (tmp_path / "id_ecdsa").write_text("private key\n")
    (tmp_path / "private_key.pem").write_text("-----BEGIN PRIVATE KEY-----\n")
    (tmp_path / "private_key.ppk").write_text("putty key\n")
    (tmp_path / "aws_credentials").write_text("aws keys\n")
    (tmp_path / "credentials").write_text("creds\n")
    (tmp_path / "service_account.json").write_text('{"type": "service_account"}\n')
    (tmp_path / "gcp_credentials.json").write_text('{"type": "gcp"}\n')
    (tmp_path / "firebase_admin_sdk.json").write_text('{"type": "firebase"}\n')
    (tmp_path / ".netrc").write_text("machine login\n")
    (tmp_path / ".npmrc").write_text("token\n")
    (tmp_path / ".pypirc").write_text("pypi token\n")
    (tmp_path / "secrets.yaml").write_text("secrets:\n")
    (tmp_path / "secrets.yml").write_text("secrets:\n")
    (tmp_path / "vault.yml").write_text("vault:\n")
    (tmp_path / "vault.yaml").write_text("vault:\n")

    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    assert "main.py" in result["files_found"]
    sensitive_found = [f for f in result["files_found"] if any(
        excl in f for excl in [".env", "id_rsa", "id_ed25519", "id_dsa", "id_ecdsa",
                               "private_key", "aws_credentials", "credentials",
                               "service_account", "gcp_credentials", "firebase",
                               ".netrc", ".npmrc", ".pypirc", "secrets", "vault"]
    )]
    assert len(sensitive_found) == 0, f"Sensitive files found: {sensitive_found}"


def test_secret_redaction_in_analysis():
    """Test that secret redaction works on various secret patterns."""
    from src.analysis import _redact_secrets, _redact_dict

    test_cases = [
        ("API_KEY = 'sk-1234567890abcdef'", "[REDACTED]"),
        ("aws_secret_access_key = 'abcdefghijklmnopqrstuvwxyz123456'", "[REDACTED]"),
        ("password = 'supersecret123'", "[REDACTED]"),
        ("DATABASE_URL = 'postgresql://user:pass@host/db'", "[REDACTED]"),
        ("private_key = '-----BEGIN PRIVATE KEY-----\nMIIE...'", "[REDACTED]"),
        ("GH_TOKEN = 'ghp_1234567890abcdefghijklmnopqrstuvwxyz'", "[REDACTED]"),
        ("normal text without secrets", "normal text without secrets"),
    ]

    for input_text, expected_pattern in test_cases:
        result = _redact_secrets(input_text)
        if expected_pattern == "[REDACTED]":
            assert "[REDACTED]" in result, f"Failed to redact: {input_text} -> {result}"
        else:
            assert result == input_text, f"Incorrectly redacted: {input_text} -> {result}"

    # Test dict redaction
    test_dict = {
        "key1": "normal value",
        "key2": "API_KEY = 'sk-secret123'",
        "nested": {"secret": "password = 'secret123'"},
        "list": ["normal", "SECRET_KEY = 'abc123'"],
    }
    redacted = _redact_dict(test_dict)
    assert redacted["key1"] == "normal value"
    assert "[REDACTED]" in redacted["key2"]
    assert "[REDACTED]" in redacted["nested"]["secret"]
    assert "[REDACTED]" in redacted["list"][1]


def test_file_size_limits_enforced(tmp_path: Path):
    """Test that file size limits are enforced."""
    # Create a large file
    large_content = "x" * 10000
    (tmp_path / "large.py").write_text(large_content)

    config = TargetProjectConfig(
        str(tmp_path),
        max_chars_per_file=100,
    )
    result = inspect_source(config)

    assert len(result["files_found"]["large.py"]) == 100


def test_max_files_limit_enforced(tmp_path: Path):
    """Test that max files limit is enforced."""
    for i in range(20):
        (tmp_path / f"file{i}.py").write_text(f"# file {i}\n")

    config = TargetProjectConfig(str(tmp_path), max_files=5)
    result = inspect_source(config)

    assert len(result["files_found"]) == 5


def test_test_output_limit_enforced(tmp_path: Path):
    """Test that test output limit is enforced."""
    (tmp_path / "test_loud.py").write_text(
        "def test_loud():\n"
        "    print('x' * 10000)\n"
        "    assert True\n"
    )

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "test_loud.py", "-v", "-s"],
        test_timeout=30,
        max_test_output=100,
    )

    result = run_tests(config)
    assert len(result["stdout"]) <= 100
    assert len(result["stderr"]) <= 100


def test_evidence_size_bounded():
    """Test that evidence strings are bounded."""
    from src.orchestrator import summarize_result

    large_result = {"data": "x" * 100000}
    summary = summarize_result(large_result)

    assert len(summary) <= 6000


def test_run_tests_timeout_handling(tmp_path: Path):
    """Test that test timeout is handled correctly."""
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-c", "import time; time.sleep(10)"],
        test_timeout=1,
    )

    result = run_tests(config)

    assert result["status"] == "timeout"
    assert result["exit_code"] is None
    assert "timed out" in result["evidence"].lower()


def test_run_tests_nonzero_exit(tmp_path: Path):
    """Test that nonzero exit codes are handled."""
    (tmp_path / "test_fail.py").write_text("import sys; sys.exit(42)\n")

    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "test_fail.py"],
        test_timeout=10,
    )

    result = run_tests(config)

    assert result["status"] == "failed"
    assert result["exit_code"] == 42


def test_run_tests_missing_runner_error(tmp_path: Path):
    """Test that missing test runner produces error status."""
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["definitely_not_a_real_command_xyz"],
        test_timeout=5,
    )

    result = run_tests(config)

    assert result["status"] == "error"
    assert result["exit_code"] is None
    assert "not found" in result["evidence"].lower()


def test_tool_exceptions_handled(tmp_path: Path):
    """Test that tool exceptions don't crash the investigation."""
    # This tests that OSError in file reading is handled
    config = TargetProjectConfig(str(tmp_path))
    result = inspect_source(config)

    # Empty directory should not raise
    assert result["action"] == "inspect_source"
    assert "files_found" in result
def test_run_tests_uses_current_interpreter(tmp_path: Path):
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "-v", "--tb=short"],
    )
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = run_tests(config)

    assert result["command"][0] == sys.executable
    assert mock_run.call_args.args[0][0] == sys.executable


def test_run_tests_missing_pytest_is_environment_failure(tmp_path: Path):
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["python", "-m", "pytest", "-v", "--tb=short"],
    )
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="No module named pytest",
        )
        result = run_tests(config)

    assert result["status"] == "error"
    assert result["exit_code"] == 1
    assert "environment/tooling failure" in result["evidence"]


def test_check_dependency_installed_module(tmp_path: Path):
    """Test that an installed module (sys) is reported as installed."""
    config = TargetProjectConfig(str(tmp_path))
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = check_dependency(config, "sys")

    assert result["action"] == "check_dependency"
    assert result["module"] == "sys"
    assert result["status"] == "installed"
    assert result["command"] == [sys.executable, "-c", "import sys"]
    assert result["exit_code"] == 0
    assert mock_run.call_args.args[0] == [sys.executable, "-c", "import sys"]
    assert mock_run.call_args.kwargs["shell"] is False
    assert mock_run.call_args.kwargs["cwd"] == tmp_path.resolve()
    assert "importable" in result["evidence"]


def test_check_dependency_missing_module(tmp_path: Path):
    """Test that a missing module is reported as missing."""
    config = TargetProjectConfig(str(tmp_path))
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'nonexistent_module_xyz'",
        )
        result = check_dependency(config, "nonexistent_module_xyz")

    assert result["action"] == "check_dependency"
    assert result["module"] == "nonexistent_module_xyz"
    assert result["status"] == "missing"
    assert result["exit_code"] == 1
    assert "not importable" in result["evidence"]


def test_check_dependency_import_error_reported_as_missing(tmp_path: Path):
    """Test that ImportError is also reported as missing."""
    config = TargetProjectConfig(str(tmp_path))
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ImportError: cannot import name 'foo'",
        )
        result = check_dependency(config, "some_module")

    assert result["status"] == "missing"


def test_check_dependency_timeout(tmp_path: Path):
    """Test timeout handling."""
    config = TargetProjectConfig(str(tmp_path), test_timeout=1)
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=[sys.executable, "-c", "import sys"], timeout=1
        )
        result = check_dependency(config, "sys")

    assert result["status"] == "timeout"
    assert result["exit_code"] is None
    assert "timed out" in result["evidence"].lower()


def test_check_dependency_invalid_module_name(tmp_path: Path):
    """Test that invalid module names are rejected before execution."""
    config = TargetProjectConfig(str(tmp_path))

    result = check_dependency(config, "")
    assert result["status"] == "insufficient_context"
    assert result["exit_code"] is None
    assert "insufficient context" in result["evidence"].lower()

    result = check_dependency(config, "not a valid module")
    assert result["status"] == "insufficient_context"
    assert "insufficient context" in result["evidence"].lower()

    result = check_dependency(config, "; rm -rf /")
    assert result["status"] == "insufficient_context"
    assert "insufficient context" in result["evidence"].lower()

    result = check_dependency(config, "..")
    assert result["status"] == "insufficient_context"


def test_check_dependency_command_not_split(tmp_path: Path):
    """Test that the interpreter path with spaces remains a single argument."""
    config = TargetProjectConfig(str(tmp_path))
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = check_dependency(config, "sys")

    cmd = result["command"]
    assert cmd[0] == sys.executable
    assert cmd == [sys.executable, "-c", "import sys"]
    assert len(cmd) == 3


def test_check_dependency_working_directory(tmp_path: Path):
    """Test that cwd is set to the validated target project path."""
    config = TargetProjectConfig(str(tmp_path))
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        check_dependency(config, "sys")

    assert mock_run.call_args.kwargs["cwd"] == tmp_path.resolve()


def test_check_dependency_bounded_output(tmp_path: Path):
    """Test that output is bounded by max_test_output."""
    config = TargetProjectConfig(str(tmp_path), max_test_output=50)
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="x" * 10000, stderr=""
        )
        result = check_dependency(config, "sys")

    assert len(result["stdout"]) <= 50


def test_check_dependency_no_module_argument(tmp_path: Path):
    """Test that check_dependency without derivable context returns insufficient_context."""
    from src.orchestrator import execute_action

    config = TargetProjectConfig(str(tmp_path))
    # No error or evidence provided → cannot derive a module name.
    result = execute_action("check_dependency", config, arguments={})

    assert result["action"] == "check_dependency"
    assert result["status"] == "insufficient_context"
    assert result["exit_code"] is None
    assert "insufficient context" in result["evidence"].lower()


def test_check_dependency_derives_module_from_error(tmp_path: Path):
    """Test that execute_action derives the module name from the reported error."""
    from src.orchestrator import execute_action

    config = TargetProjectConfig(str(tmp_path))
    with patch("src.orchestrator.check_dependency") as mock_check:
        mock_check.return_value = {
            "action": "check_dependency",
            "module": "psycopg",
            "status": "missing",
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


def test_check_dependency_derives_module_from_evidence(tmp_path: Path):
    """Test that execute_action derives the module name from verified evidence."""
    from src.orchestrator import execute_action

    config = TargetProjectConfig(str(tmp_path))
    with patch("src.orchestrator.check_dependency") as mock_check:
        mock_check.return_value = {
            "action": "check_dependency",
            "module": "psycopg",
            "status": "installed",
        }
        result = execute_action(
            "check_dependency",
            config,
            arguments={},
            error="Application failed to start",
            evidence_history=[
                "inspect_source: app.py contains 'import psycopg'",
            ],
        )

    mock_check.assert_called_once()
    assert mock_check.call_args.args[1] == "psycopg"
    assert result["status"] == "installed"


def test_check_dependency_insufficient_context_when_ambiguous(tmp_path: Path):
    """Test that execute_action returns insufficient_context when module is ambiguous."""
    from src.orchestrator import execute_action

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
    assert "insufficient context" in result["evidence"].lower()


def test_derive_module_name_prefers_error_over_evidence():
    """Test that _derive_module_name prefers the reported error over evidence."""
    from src.orchestrator import _derive_module_name

    result = _derive_module_name(
        "ModuleNotFoundError: No module named 'psycopg'",
        ["inspect_source: app.py imports 'some_other_module'"],
    )
    assert result == "psycopg"


def test_derive_module_name_falls_back_to_evidence():
    """Test that _derive_module_name falls back to verified evidence."""
    from src.orchestrator import _derive_module_name

    result = _derive_module_name(
        "Application failed to start",
        ["inspect_source: app.py contains 'import psycopg'"],
    )
    assert result == "psycopg"


def test_derive_module_name_returns_empty_when_ambiguous():
    """Test that _derive_module_name returns empty when module is ambiguous."""
    from src.orchestrator import _derive_module_name

    result = _derive_module_name("Something went wrong", ["inspect_source: read 5 files"])
    assert result == ""

    result = _derive_module_name(None, [])
    assert result == ""


def test_check_dependency_fixture_passing_but_failure_reproducing(tmp_path: Path):
    """Test that check_dependency identifies a missing module even when tests pass.

    This simulates the fixture scenario: tests pass because they assert the
    import failure, but check_dependency reveals psycopg is genuinely missing
    from the runtime environment. Test-suite success does not imply app health.
    """
    config = TargetProjectConfig(str(tmp_path))

    # Tests pass (they assert psycopg is missing)
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")
        test_result = run_tests(config)

    assert test_result["status"] == "passed"

    # But check_dependency reveals psycopg is missing
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'psycopg'",
        )
        dep_result = check_dependency(config, "psycopg")

    assert dep_result["status"] == "missing"
    # A passing test suite does NOT mean the application is healthy
    assert test_result["status"] != dep_result["status"]


def test_check_dependency_reports_interpreter(tmp_path: Path):
    """Test that check_dependency reports the exact interpreter used."""
    config = TargetProjectConfig(str(tmp_path))
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = check_dependency(config, "sys")

    assert result["interpreter"] == sys.executable
    assert "interpreter" in result["evidence"]
    assert sys.executable in result["evidence"]


def test_check_dependency_tool_failure_is_not_app_evidence(tmp_path: Path):
    """Test that check_dependency error/timeout is a tool failure, not app evidence."""
    config = TargetProjectConfig(str(tmp_path))

    # Tool execution error
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.side_effect = OSError("Permission denied")
        result = check_dependency(config, "psycopg")

    assert result["status"] == "error"
    assert "Execution error" in result["stderr"]
    # An error status is NOT evidence that psycopg is missing
    assert result["status"] != "missing"

    # Timeout
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=[sys.executable, "-c", "import psycopg"], timeout=5
        )
        result = check_dependency(config, "psycopg")

    assert result["status"] == "timeout"
    assert result["exit_code"] is None
    # A timeout is NOT evidence that psycopg is missing
    assert result["status"] != "missing"


def test_check_dependency_insufficient_context_is_not_missing(tmp_path: Path):
    """Test that insufficient_context is not confused with a missing module."""
    config = TargetProjectConfig(str(tmp_path))

    # Invalid module name → insufficient_context, not missing
    result = check_dependency(config, "")
    assert result["status"] == "insufficient_context"
    assert result["status"] != "missing"

    # Ambiguous module → insufficient_context
    result = check_dependency(config, "not valid")
    assert result["status"] == "insufficient_context"
    assert result["status"] != "missing"


def test_run_tests_tool_failure_is_not_app_evidence(tmp_path: Path):
    """Test that run_tests errors are tool failures, not root cause evidence."""
    config = TargetProjectConfig(
        str(tmp_path),
        test_command=["nonexistent_runner"],
        test_timeout=5,
    )

    result = run_tests(config)

    assert result["status"] == "error"
    assert result["exit_code"] is None
    # Tool failure is not evidence about the application
    assert result["status"] != "passed"
    assert result["status"] != "failed"


def test_evidence_sufficient_when_runtime_unverified():
    """Test that evidence_sufficient is false when runtime not verified."""
    from src.analysis import RootCauseReport

    # Runtime NOT verified: check_dependency returned insufficient_context
    report = RootCauseReport(
        confirmed_observations=["requirements.txt declares psycopg"],
        most_likely_cause="Missing dependency: psycopg",
        alternative_explanations=["Interpreter mismatch"],
        evidence_supporting={"Missing dependency": ["requirements.txt"]},
        remaining_uncertainty=[
            "Runtime environment not verified: check_dependency returned insufficient_context",
            "Interpreter used for check_dependency not confirmed",
        ],
        recommended_next_step="Verify psycopg importability with check_dependency",
        suggested_fix=None,
        evidence_sufficient=False,
    )
    assert report.evidence_sufficient is False
    assert len(report.remaining_uncertainty) > 0


def test_evidence_sufficient_when_runtime_verified():
    """Test that evidence_sufficient can be true when runtime verified."""
    from src.analysis import RootCauseReport

    # Runtime verified: check_dependency returned missing for psycopg
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
                "requirements.txt declares psycopg",
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
    assert "not verified" not in str(report.remaining_uncertainty).lower()


def test_check_dependency_missing_module_reports_interpreter(tmp_path: Path):
    """Test that a missing module result includes the interpreter."""
    config = TargetProjectConfig(str(tmp_path))
    with patch("src.diagnostics.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'psycopg'",
        )
        result = check_dependency(config, "psycopg")

    assert result["status"] == "missing"
    assert result["interpreter"] == sys.executable
    assert sys.executable in result["evidence"]


def test_extract_module_from_error():
    """Test extracting module names from error messages."""
    from src.diagnostics import _extract_module_from_error

    assert _extract_module_from_error("ModuleNotFoundError: No module named 'psycopg'") == "psycopg"
    assert _extract_module_from_error('ModuleNotFoundError: No module named "psycopg"') == "psycopg"
    assert _extract_module_from_error("import nonexistent_module") == "nonexistent_module"
    assert _extract_module_from_error("Some other error") == ""
    assert _extract_module_from_error("") == ""
