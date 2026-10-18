"""Registry of reproducible demo scenarios for Rootcause.

Each scenario points to a real fixture under ``examples/fixtures/`` and
carries the error output that reproduces the failure. Selecting a scenario in
the UI populates the project directory and error input fields; it does NOT
start an investigation automatically.

Expected outcomes are machine-readable descriptions of what the diagnostic
tools *should* be able to observe. They are used for tests and validation and
are never injected into the live investigation result.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class ExpectedOutcome:
    """Machine-readable expectation for a scenario's diagnostic evidence."""

    scenario_id: str
    failure_category: str
    expected_evidence: list[str]
    expected_diagnosis_category: str
    suggested_corrective_action: str
    supported: bool
    limitations: list[str]


@dataclass(frozen=True)
class DemoScenario:
    """A reproducible demo scenario backed by a real fixture."""

    id: str
    name: str
    category: str
    description: str
    fixture_dir: str  # relative to the repository root
    error: str
    expected_outcome: ExpectedOutcome


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: Final[dict[str, DemoScenario]] = {}

_REGISTER: list[DemoScenario] = []


def _register(scenario: DemoScenario) -> DemoScenario:
    SCENARIOS[scenario.id] = scenario
    _REGISTER.append(scenario)
    return scenario


_register(
    DemoScenario(
        id="missing_dependency",
        name="Missing Python Dependency",
        category="dependency",
        description=(
            "The application imports `psycopg` (a PostgreSQL adapter) but the "
            "package is not installed in the current environment, producing a "
            "ModuleNotFoundError. The dependency manifest declares it, so the "
            "fix is to install the declared dependencies."
        ),
        fixture_dir="examples/fixtures/missing_dependency",
        error=(
            "ModuleNotFoundError: No module named 'psycopg'\n"
            "\n"
            "Traceback (most recent call last):\n"
            "  File \"app.py\", line 3, in <module>\n"
            "    import psycopg\n"
            "ModuleNotFoundError: No module named 'psycopg'"
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="missing_dependency",
            failure_category="dependency",
            expected_evidence=[
                "requirements.txt declares psycopg[binary]>=3.2",
                "app.py imports psycopg at module level",
                "check_dependency reports psycopg as missing",
            ],
            expected_diagnosis_category="missing_dependency",
            suggested_corrective_action=(
                "Install the declared dependency: pip install -r requirements.txt"
            ),
            supported=True,
            limitations=[],
        ),
    )
)

_register(
    DemoScenario(
        id="dependency_conflict",
        name="Dependency Version Conflict",
        category="dependency",
        description=(
            "package-a requires shared-lib>=2.0 while package-b requires "
            "shared-lib<1.0, so no single version can satisfy both. The app "
            "raises a RuntimeError describing the unresolvable conflict."
        ),
        fixture_dir="examples/fixtures/dependency_conflict",
        error=(
            "RuntimeError: Dependency conflict: shared-lib is required but "
            "not installed. package-a requires shared-lib>=2.0 while "
            "package-b requires shared-lib<1.0, so no single version can "
            "satisfy both."
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="dependency_conflict",
            failure_category="dependency",
            expected_evidence=[
                "requirements.txt declares package-a>=2.0 and package-b>=1.0",
                "app.py contains a version guard raising the conflict error",
            ],
            expected_diagnosis_category="dependency_version_conflict",
            suggested_corrective_action=(
                "Resolve the conflicting version constraints in requirements.txt "
                "so a single shared-lib version satisfies all dependents."
            ),
            supported=True,
            limitations=[
                "The shared-lib module itself may not be installed, so "
                "check_dependency cannot confirm a concrete installed version; "
                "the diagnosis relies on manifest declarations and the raised "
                "RuntimeError."
            ],
        ),
    )
)

_register(
    DemoScenario(
        id="import_error",
        name="Incorrect Python Import",
        category="import",
        description=(
            "The application imports `nonexistent_local_module`, which does not "
            "exist anywhere on the import path, producing a ModuleNotFoundError."
        ),
        fixture_dir="examples/fixtures/import_error",
        error=(
            "ModuleNotFoundError: No module named 'nonexistent_local_module'\n"
            "\n"
            "Traceback (most recent call last):\n"
            "  File \"app.py\", line 3, in <module>\n"
            "    import nonexistent_local_module\n"
            "ModuleNotFoundError: No module named 'nonexistent_local_module'"
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="import_error",
            failure_category="import",
            expected_evidence=[
                "app.py imports nonexistent_local_module at module level",
                "check_dependency reports nonexistent_local_module as missing",
            ],
            expected_diagnosis_category="incorrect_import",
            suggested_corrective_action=(
                "Correct or remove the import statement; verify the intended "
                "module name and that it exists on the import path."
            ),
            supported=True,
            limitations=[],
        ),
    )
)

_register(
    DemoScenario(
        id="missing_env",
        name="Missing Environment Variable",
        category="configuration",
        description=(
            "The application reads DATABASE_URL from the environment and raises "
            "a RuntimeError when it is not set. No database or credentials are "
            "involved."
        ),
        fixture_dir="examples/fixtures/missing_env",
        error=(
            "RuntimeError: Missing environment variable: DATABASE_URL is not "
            "set. Configure DATABASE_URL (e.g. postgresql://localhost:5432/mydb) "
            "before running the application."
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="missing_env",
            failure_category="configuration",
            expected_evidence=[
                "app.py reads os.environ.get(\"DATABASE_URL\") and raises when missing",
                "The error message explicitly names DATABASE_URL as the missing key",
            ],
            expected_diagnosis_category="missing_env_variable",
            suggested_corrective_action=(
                "Set the DATABASE_URL environment variable before running the "
                "application; do not invent a production value."
            ),
            supported=True,
            limitations=[
                "check_dependency cannot verify environment variables; "
                "diagnosis relies on inspect_source finding the env lookup."
            ],
        ),
    )
)

_register(
    DemoScenario(
        id="config_error",
        name="Configuration File Error",
        category="configuration",
        description=(
            "config.json is truncated and missing its closing braces, so "
            "json.load raises a JSONDecodeError when the app parses it."
        ),
        fixture_dir="examples/fixtures/config_error",
        error=(
            "json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)\n"
            "\n"
            "Traceback (most recent call last):\n"
            "  File \"app.py\", line 5, in <module>\n"
            "    config = json.load(fh)\n"
            "json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)"
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="config_error",
            failure_category="configuration",
            expected_evidence=[
                "app.py opens and parses config.json with json.load(fh)",
                "The error is a JSON parsing failure",
            ],
            expected_diagnosis_category="config_parse_error",
            suggested_corrective_action=(
                "Fix the malformed JSON in config.json (add the missing closing "
                "braces); do not automatically rewrite the file."
            ),
            supported=True,
            limitations=[
                "config.json is not a Python source file or dependency manifest, "
                "so the diagnostic tools do not read its contents directly; the "
                "diagnosis relies on app.py source plus the reported error."
            ],
        ),
    )
)

_register(
    DemoScenario(
        id="failing_test",
        name="Failing Unit Test",
        category="testing",
        description=(
            "calculator.add subtracts instead of adding, so the test asserting "
            "add(2, 3) == 5 fails with \"Expected 5, got -1\"."
        ),
        fixture_dir="examples/fixtures/failing_test",
        error=(
            "FAILED test_calculator.py::test_add - AssertionError: Expected 5, got -1\n"
            "\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n"
            "E   AssertionError: Expected 5, got -1"
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="failing_test",
            failure_category="testing",
            expected_evidence=[
                "run_tests reports test_add failed: expected 5, got -1",
                "calculator.py shows add returns a - b instead of a + b",
            ],
            expected_diagnosis_category="implementation_defect",
            suggested_corrective_action=(
                "Change calculator.add to return a + b instead of a - b."
            ),
            supported=True,
            limitations=[],
        ),
    )
)

_register(
    DemoScenario(
        id="missing_file",
        name="Incorrect File Path",
        category="filesystem",
        description=(
            "The application attempts to open nonexistent_data.txt with a "
            "relative path that does not exist in the project directory, "
            "raising FileNotFoundError."
        ),
        fixture_dir="examples/fixtures/missing_file",
        error=(
            "FileNotFoundError: [Errno 2] No such file or directory: "
            "'nonexistent_data.txt'"
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="missing_file",
            failure_category="filesystem",
            expected_evidence=[
                "app.py opens nonexistent_data.txt with a relative path",
                "The error identifies the exact path that could not be found",
            ],
            expected_diagnosis_category="incorrect_file_path",
            suggested_corrective_action=(
                "Correct the file path or resolve it robustly relative to the "
                "script location; check existence before opening."
            ),
            supported=True,
            limitations=[
                "The diagnostic tools cannot list missing files; diagnosis relies "
                "on inspect_source finding the open() call plus the reported error."
            ],
        ),
    )
)

_register(
    DemoScenario(
        id="port_conflict",
        name="Port Already in Use",
        category="network",
        description=(
            "The app holds an ephemeral port with one socket then attempts to "
            "bind a second socket to the same port, producing an Address already "
            "in use error."
        ),
        fixture_dir="examples/fixtures/port_conflict",
        error=(
            "RuntimeError: Port already in use: cannot bind to "
            "127.0.0.1:<port> because the address is already in use by another "
            "listener."
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="port_conflict",
            failure_category="network",
            expected_evidence=[
                "app.py calls socket.bind on a port already held by another socket",
                "The error is an address-in-use OSError, not a connectivity failure",
            ],
            expected_diagnosis_category="port_conflict",
            suggested_corrective_action=(
                "Check the existing listener holding the port or choose another "
                "available port; do not terminate arbitrary user processes."
            ),
            supported=True,
            limitations=[
                "The exact port number is ephemeral and varies per run; the "
                "diagnosis relies on inspect_source finding the bind call."
            ],
        ),
    )
)

_register(
    DemoScenario(
        id="database_connection",
        name="Database Connection Failure",
        category="database",
        description=(
            "The app attempts to connect to 127.0.0.1:54321 where nothing is "
            "listening, raising a ConnectionRefusedError. No real database or "
            "credentials are involved."
        ),
        fixture_dir="examples/fixtures/database_connection",
        error=(
            "RuntimeError: Database connection failure: could not connect to "
            "127.0.0.1:54321 (connection refused). Verify the database host, "
            "port, and that the database server is running."
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="database_connection",
            failure_category="database",
            expected_evidence=[
                "app.py attempts socket.connect((\"127.0.0.1\", 54321))",
                "The error is a connection refusal, not an authentication failure",
            ],
            expected_diagnosis_category="connection_refused",
            suggested_corrective_action=(
                "Verify the database host, port, and that the database server "
                "is running; distinguish connection refusal from auth failures."
            ),
            supported=True,
            limitations=[
                "No real database is involved; diagnosis relies on inspect_source "
                "finding the connect call plus the reported error."
            ],
        ),
    )
)

_register(
    DemoScenario(
        id="syntax_error",
        name="Syntax Error",
        category="syntax",
        description=(
            "broken.py contains a deliberate syntax error (an unterminated "
            "function definition), so Python reports a SyntaxError when parsing."
        ),
        fixture_dir="examples/fixtures/syntax_error",
        error=(
            "SyntaxError: invalid syntax\n"
            "\n"
            "File \"broken.py\", line 4\n"
            "    def broken_function(\n"
            "SyntaxError: invalid syntax"
        ),
        expected_outcome=ExpectedOutcome(
            scenario_id="syntax_error",
            failure_category="syntax",
            expected_evidence=[
                "broken.py contains a malformed def statement that Python cannot parse",
                "The parser reports the file and line of the syntax error",
            ],
            expected_diagnosis_category="syntax_error",
            suggested_corrective_action=(
                "Fix the malformed function definition in broken.py based on "
                "the parser output; do not execute the broken file."
            ),
            supported=True,
            limitations=[
                "inspect_source reads file contents but does not parse Python; "
                "the diagnosis relies on the reported SyntaxError plus source."
            ],
        ),
    ),
)


def list_scenarios() -> list[DemoScenario]:
    """Return all registered demo scenarios in a stable order."""
    return list(_REGISTER)


def get_scenario(scenario_id: str) -> DemoScenario | None:
    """Return the scenario with the given id, or None if not found."""
    return SCENARIOS.get(scenario_id)


def scenario_ids() -> list[str]:
    """Return all scenario ids in registration order."""
    return [s.id for s in _REGISTER]


def fixture_absolute_path(scenario: DemoScenario, repo_root: str | Path) -> Path:
    """Resolve a scenario's fixture directory to an absolute path."""
    return (Path(repo_root) / scenario.fixture_dir).resolve()


def expected_outcomes() -> list[ExpectedOutcome]:
    """Return the expected outcome for every registered scenario."""
    return [s.expected_outcome for s in _REGISTER]


__all__ = [
    "DemoScenario",
    "ExpectedOutcome",
    "SCENARIOS",
    "list_scenarios",
    "get_scenario",
    "scenario_ids",
    "fixture_absolute_path",
    "expected_outcomes",
]
