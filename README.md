# Rootcause

Decision-first debugging agent. Python, Strands Agents, Strands Decider 2B, Amazon Bedrock Nova Micro.

## Prerequisites
- Python 3.14
- AWS credentials with Bedrock model access (amazon.nova-micro-v1:0)
- Local Strands Decider 2B server on http://127.0.0.1:8099

## Setup
```powershell
python -m venv .venv314
.\.venv314\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Start and verify Decider
Run the Decider 2B server on port 8099 (checkpoint per Strands Decider docs). Verify:
```powershell
curl http://127.0.0.1:8099/v1/systemone
```

## Unit tests (no AWS/Decider)
```powershell
python -m pytest -q
```

## Demo
Fixture reproduction:
```powershell
cd examples\fixtures\missing_dependency
python test_fixture.py
```

Investigation:
```powershell
python -m src.orchestrator --project-path examples\fixtures\missing_dependency --max-steps 3
```

## Demo Scenarios

Rootcause includes a curated set of reproducible debugging scenarios under
`examples/fixtures/`. Each scenario points to a real fixture project with an
intentionally introduced failure, plus the error output that reproduces it.

### UI selector

In the Rootcause workspace, open **Try a demo scenario** (located above the
Project directory field). Choose a scenario from the dropdown; it populates the
project directory and error input fields with the matching fixture. Review the
populated inputs, then click **Investigate error** to run the real diagnostic
workflow. Selecting a scenario never starts an investigation automatically, and
you can return to manual input at any time via **Clear selection**.

### Scenarios

| Scenario | Category | Demonstrates | Offline |
|----------|----------|--------------|---------|
| Missing Python Dependency | dependency | `ModuleNotFoundError` for an undeclared package | Yes |
| Dependency Version Conflict | dependency | Unresolvable shared-lib version constraints | Yes |
| Incorrect Python Import | import | Import of a nonexistent local module | Yes |
| Missing Environment Variable | configuration | Required `DATABASE_URL` not set | Yes |
| Configuration File Error | configuration | Malformed `config.json` (JSON parse failure) | Yes |
| Failing Unit Test | testing | `calculator.add` subtracts instead of adding | Yes |
| Incorrect File Path | filesystem | `FileNotFoundError` from a bad relative path | Yes |
| Port Already in Use | network | `OSError` binding to an occupied port | Yes |
| Database Connection Failure | database | `ConnectionRefusedError` to an unavailable endpoint | Yes |
| Syntax Error | syntax | Unterminated function definition in `broken.py` | Yes |

Each fixture includes a `README.md` documenting the failure, how to reproduce
it, the expected evidence, and what a correct diagnosis should and should not
claim. Fixture reproduction (no AWS/Decider required):

```powershell
cd examples\fixtures\missing_dependency
python test_fixture.py
```

Investigation against a fixture (requires the local Strands Decider server;
Bedrock analysis is optional and degrades gracefully):

```powershell
python -m src.orchestrator --project-path examples\fixtures\missing_dependency --max-steps 3
```

The `/api/demo-scenarios` endpoint lists all scenarios with their resolved
project paths, error text, and machine-readable expected outcomes for test
validation. Expected outcomes are used for tests only and are never injected
into the live investigation result; the real diagnostic workflow always runs.

## Architecture
Flow: reported error -> available actions registry -> Decider choose_next_action validates selected action -> execute_action runs diagnostic -> evidence history -> Bedrock analyze_root_cause -> report. Decider choice controls execution; unknown/malformed/duplicate actions rejected by validation.

## Limitations
- Tests run arbitrary project code; only trusted projects.
- No dependency installation or fixes applied automatically.
- Network required for live demo (AWS/Decider).
- Licensed under MIT; see LICENSE file.

## Troubleshooting
- Decider connection errors: ensure server running on port 8099.
- Bedrock errors: check AWS credentials/region/model access.
- Tests: use .venv314 python.

