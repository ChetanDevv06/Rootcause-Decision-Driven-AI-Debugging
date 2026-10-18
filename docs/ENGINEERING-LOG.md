# Rootcause — Engineering Log & Architectural Decision Records (ADR)

This document records the verified engineering decisions, design rationales, alternatives evaluated, and architectural trade-offs established throughout the development of Rootcause.

---

## Architecture Decision Record Index

- [ADR 01: Decision-First Orchestration vs. Autonomous Monolithic Agent Loops](#adr-01-decision-first-orchestration-vs-autonomous-monolithic-agent-loops)
- [ADR 02: Bounded Step Budget with Honest Truncation Transparency](#adr-02-bounded-step-budget-with-honest-truncation-transparency)
- [ADR 03: Read-Only Evidence Collection vs. Automated Patch Application](#adr-03-read-only-evidence-collection-vs-automated-patch-application)
- [ADR 04: Two-Tier Hybrid Intelligence (Local Decider 2B + Cloud Bedrock Nova Micro)](#adr-04-two-tier-hybrid-intelligence-local-decider-2b--cloud-bedrock-nova-micro)
- [ADR 05: Graceful Degradation and Zero-Fabrication Invariant](#adr-05-graceful-degradation-and-zero-fabrication-invariant)
- [ADR 06: Isolation of Experimental Strands Agent Prototype (`rootcause_agent.py`)](#adr-06-isolation-of-experimental-strands-agent-prototype-rootcause_agentpy)

---

## ADR 01: Decision-First Orchestration vs. Autonomous Monolithic Agent Loops

### Status
Accepted & Implemented (`src/orchestrator.py`, `src/decider_client.py`).

### Context
Traditional generative AI debugging agents rely on monolithic large language models (LLMs) executing general-purpose ReAct (Reasoning + Acting) loops. While flexible, unconstrained agent loops suffer from severe failure modes in software debugging:
1. **Speculative Drift**: The model guesses a cause early and invents commands or edits that confirm its bias.
2. **Infinite Looping**: Agents frequently cycle between similar commands (`ls`, `cat`, re-running failed scripts) without reaching convergence.
3. **High Latency & Token Burn**: Round-tripping hundreds of kilobytes of stack traces, dependency trees, and source code through a 70B+ frontier cloud model on every decision cycle is costly and slow.

### Decision
Decouple **action gating** from **final natural language synthesis**:
1. All available actions are governed by an explicit whitelist registry in `src/orchestrator.py` (`inspect_dependencies`, `inspect_source`, `run_tests`, `check_dependency`, `stop_and_report`).
2. Action selection is delegated to **Strands Decider 2B**, a compact, local specialized model operating via the `/v1/systemone` structured decision protocol.
3. The Decider is offered only unexecuted actions (plus `stop_and_report`), mathematically guaranteeing that no diagnostic tool is executed twice in the same investigation.
4. If the Decider selects an action outside the offered registry, `_validate_decider_response()` raises a `DeciderValidationError` and fails closed immediately.

### Trade-offs & Limitations
- **Positive**: Eliminates hallucinated tools, guarantees finite exploration space, and minimizes latency.
- **Negative**: The model cannot compose novel ad-hoc shell commands on the fly; diagnostic capabilities are limited to the registered tools implemented in Python.

---

## ADR 02: Bounded Step Budget with Honest Truncation Transparency

### Status
Accepted & Implemented (`src/orchestrator.py`, `src/analysis.py`).

### Context
In automated diagnostics, more steps do not always produce better insights; redundant tool runs risk hitting rate limits or timeouts. Conversely, terminating an investigation prematurely without notifying downstream consumers can lead an LLM to conclude that lack of evidence equals lack of error.

### Decision
1. Impose a hard ceiling on decision cycles (`MAX_STEPS_LIMIT = 10`, configurable default `MAX_STEPS = 3`).
2. When the step budget is exhausted before the model voluntarily chooses `stop_and_report`, `src/orchestrator.py` records `stop_reason: "maximum_steps_reached"` and attaches an explicit `truncation_notice`.
3. The prompt builder in `src/analysis.py` specifically formats this notice into the Bedrock prompt, instructing Nova Micro:
   > *"If the investigation was truncated (maximum_steps_reached), acknowledge the truncation in remaining_uncertainty and do not claim evidence_sufficient is true unless the collected evidence already fully supports the cause."*

### Trade-offs & Limitations
- **Positive**: Strict bounded compute consumption; protects against incomplete diagnoses masquerading as verified facts.
- **Negative**: For complex repositories requiring file inspection, dependency checking, and test runs, a low step count (e.g. 1 or 2) will terminate before all facets are examined.

---

## ADR 03: Read-Only Evidence Collection vs. Automated Patch Application

### Status
Accepted & Implemented (`src/diagnostics.py`, `src/config.py`).

### Context
Many debugging tools attempt to automatically rewrite files or run `pip install` in the user's workspace. In enterprise repositories or shared environments, mutating code without human review risks introducing regressions, overwriting uncommitted work, or installing compromised packages.

### Decision
Rootcause enforces a **strictly read-only diagnostic posture**:
1. `inspect_dependencies` reads manifests (`requirements.txt`, `pyproject.toml`, `Pipfile`) with UTF-8 replacement error handling and bounds reading up to `config.max_dep_chars`.
2. `inspect_source` recursively discovers Python files, filters hidden or sensitive directories (`.git`, `.venv`, `__pycache__`), and bounds reading up to `config.max_files` and `config.max_chars_per_file`.
3. `check_dependency` executes `sys.executable -c "import <module>"` in a sandboxed subprocess without modifying environment state.
4. `run_tests` executes the existing test suite (default: `pytest`) with bounded execution time (`test_timeout=60s`) and bounded output capture (`max_test_output=8000`).
5. Recommended fixes are presented to the user as actionable recommendations in the final report, not applied automatically.

### Trade-offs & Limitations
- **Positive**: Zero risk of unintended file modification or destructive workspace side-effects during diagnosis.
- **Negative**: The developer must execute suggested remediation commands (e.g. `pip install -r requirements.txt`) manually.

---

## ADR 04: Two-Tier Hybrid Intelligence (Local Decider 2B + Cloud Bedrock Nova Micro)

### Status
Accepted & Implemented (`src/decider_client.py`, `src/analysis.py`).

### Context
A debugging system requires two fundamentally different types of reasoning:
1. **Iterative, fast, low-entropy choice**: Given evidence $E_k$ and a discrete set of actions $A$, select $a \in A$.
2. **Global, high-entropy synthesis**: Given full evidence trace $E$, generate a coherent, developer-facing root cause explanation with uncertainty analysis and remediation advice.

### Decision
Deploy a dual-model hybrid architecture:
| Tier | Component | Model / Engine | Role | Location |
|:---|:---|:---|:---|:---|
| **Tier 1: Decider** | `decider_client.py` | Strands Decider 2B (`/v1/systemone`) | Selects next diagnostic action based on evidence history. | Local HTTP service (port 8099) |
| **Tier 2: Synthesizer** | `analysis.py` | Amazon Bedrock Nova Micro (`amazon.nova-micro-v1:0`) | Synthesizes full evidence history into structured `RootCauseReport`. | AWS Cloud (ap-southeast-2) via Converse API |

### Trade-offs & Limitations
- **Positive**: Ultra-fast, zero-cloud-token action selection during diagnostic loops; deep semantic analysis reserved for a single one-shot synthesis at the end.
- **Negative**: Requires both a locally running Decider server and valid AWS credentials with Nova Micro model access for end-to-end cloud synthesis.

---

## ADR 05: Graceful Degradation and Zero-Fabrication Invariant

### Status
Accepted & Implemented (`src/api.py`, `src/orchestrator.py`, `src/analysis.py`).

### Context
In automated systems, when an external API or downstream model fails, tools often fabricate fallback answers or mock results to preserve UI polish. This is dangerous in software engineering, as simulated root causes can misguide developers into hunting phantom bugs.

### Decision
Rootcause strictly enforces the **Zero-Fabrication Invariant**:
1. If the local Decider 2B service is unreachable, `DeciderConnectionError` is caught, logged in `history` with step index, and the orchestrator exits the loop cleanly.
2. If Bedrock credentials are missing or the API encounters an error (`ClientError`, `BotoCoreError`), the analysis returns `analysis_status: "bedrock_error"` with the raw error message.
3. The FastAPI layer (`_unwrap_analysis`) formats an explicit error structure:
   ```json
   {
     "most_likely_cause": null,
     "confirmed_observations": [],
     "evidence_sufficient": false,
     "_analysis_status": "bedrock_error",
     "_analysis_error": "Bedrock API error: ..."
   }
   ```
4. All real diagnostic evidence gathered prior to failure is preserved intact.

### Trade-offs & Limitations
- **Positive**: Absolute data integrity; developers can trust that every displayed finding represents real workspace telemetry.
- **Negative**: The UI displays an explicit error banner when cloud services are misconfigured rather than a pretty mock diagnosis.

---

## ADR 06: Isolation of Experimental Strands Agent Prototype (`rootcause_agent.py`)

### Status
Documented & Verified (`src/rootcause_agent.py`).

### Context
The repository contains a standalone prototype script, `src/rootcause_agent.py`, which configures a `strands.Agent` using `BedrockModel` with a single tool `inspect_project_dependencies`.

### Decision
1. `src/rootcause_agent.py` is maintained solely as an experimental research artifact exploring alternative high-level Strands agent abstractions.
2. It is **not** imported, called, or referenced by `src/api.py` or `src/orchestrator.py`.
3. The main production request path operates exclusively through `orchestrator.investigate()` -> `decider_client.choose_next_action()` -> `diagnostics` -> `analysis.analyze_root_cause()`.
4. Documentation must explicitly clarify this boundary to prevent architectural confusion.
