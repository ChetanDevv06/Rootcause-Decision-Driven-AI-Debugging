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

