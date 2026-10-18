# Security Architecture & Trust Boundaries

This document provides a factual overview of the security model, trust boundaries, data handling practices, and known limitations of Rootcause.

---

## 1. Trust Boundaries & Attack Surface

Rootcause is designed to inspect local software repositories and diagnose execution failures. In this operating model:

| Entity | Trust Level | Description |
|:---|:---|:---|
| **Operator / User** | Trusted | The engineer initiating the investigation from the CLI or Web UI. |
| **Rootcause Core** | Trusted | Python backend (`FastAPI`, `orchestrator`, `diagnostics`). |
| **Local Strands Decider** | Semi-Trusted | Local service on `127.0.0.1:8099`. Outputs are strictly validated before execution. |
| **Amazon Bedrock** | Cloud Service | AWS-managed AI endpoint accessed over TLS (`boto3`). |
| **Target Project Workspace** | **Untrusted** | Source code, manifests, and test suites are treated as untrusted data. |

> [!CAUTION]
> **Host Execution Warning**: Rootcause executes target project test suites directly on the host machine using Python subprocesses. It does **not** employ a virtualized container sandbox (such as Docker or gVisor) by default. **Do not run Rootcause against untrusted, malicious, or unverified repositories.**

---

## 2. Subprocess Execution & Test Runner Safety

When diagnostic actions require code execution (`run_tests` and `check_dependency`), Rootcause enforces the following defenses:

1. **No Shell Invocations**:
   All subprocesses are launched with `shell=False` and strict argument arrays (`cmd = [...]`), preventing shell metacharacter injection.
2. **Module Name Sanitization**:
   In `check_dependency`, module names are validated against a strict regex identifier pattern:
   ```python
   MODULE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]*)*$")
   ```
   If a candidate module name fails this check, execution is rejected immediately with an `insufficient_context` status.
3. **Decider Argument Gating**:
   `src/orchestrator.py` derives the module name to check (`_derive_module_name`) strictly from the trusted user-reported error or verified diagnostic findings—**never** from arbitrary arguments supplied by the Decider model.
4. **Execution Timeouts**:
   All subprocess executions are bounded by `config.test_timeout` (default: 60 seconds). If a test hangs or enters an infinite loop, `subprocess.TimeoutExpired` terminates the process.
5. **Output Truncation**:
   Stdout and stderr are capped at `config.max_test_output` (default: 8,000 characters) to prevent memory exhaustion or denial of service from excessive logging.

---

## 3. Environment Sanitization & Secret Scrubbing

Subprocesses execute with a filtered environment to prevent leaking host credentials to target project test suites or build scripts:

### Environment Variable Filtering (`_filter_environment`)
The following sensitive variables are explicitly dropped from the subprocess environment:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_DEFAULT_REGION`
- `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `NPM_TOKEN`, `PYPI_TOKEN`
- `DATABASE_URL`, `DATABASE_PASSWORD`, `SECRET_KEY`, `API_KEY`
- `PRIVATE_KEY`, `SSH_PRIVATE_KEY`
- `GOOGLE_APPLICATION_CREDENTIALS`, `AZURE_CLIENT_SECRET`

Only safe operating system environment variables (`PATH`, `HOME`, `USER`, `TEMP`, `PYTHONPATH`, `VIRTUAL_ENV`, etc.) are retained.

---

## 4. File Inspection Boundaries & Exclusions

When inspecting files via `inspect_dependencies` and `inspect_source`, Rootcause enforces boundary validation and path exclusions:

1. **Path Traversal Protection**:
   Every discovered file is verified to reside strictly within the target repository root:
   ```python
   file_path.relative_to(root)  # Raises ValueError if outside root
   ```
2. **Excluded Directories (`EXCLUDED_DIRS`)**:
   Inspection automatically skips:
   - `.git`, `.venv`, `.venv314`, `node_modules`
   - `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`
   - `dist`, `build`, `.eggs`, `htmlcov`, `.coverage`
3. **Excluded Sensitive Files (`EXCLUDED_FILES`)**:
   Rootcause ignores private keys and credentials:
   - `.env`, `.env.local`, `.env.production`, `.env.development`
   - `id_rsa`, `id_ed25519`, `id_dsa`, `id_ecdsa`
   - `private_key.pem`, `private_key.ppk`
   - `aws_credentials`, `credentials`, `service_account.json`
   - `secrets.yaml`, `secrets.yml`, `vault.yml`
   - Files with suffixes `.pem`, `.key`, `.p12`, `.pfx`, `.crt`, `.cer`

---

## 5. Data Transmitted to External Models

### Local Strands Decider 2B (`http://127.0.0.1:8099/v1/systemone`)
- **Location**: Localhost only (`127.0.0.1`). No network traffic leaves the machine.
- **Payload**: Bounded evidence history (maximum 50,000 characters), the reported error string, and the list of available diagnostic action names.

### Amazon Bedrock Nova Micro (`amazon.nova-micro-v1:0`)
- **Location**: AWS Region `ap-southeast-2` (Sydney) via the AWS SDK (`boto3`) Converse API.
- **Payload**: Compact summary containing the sanitized project path, the reported error trace, high-level action history, and the last 6 evidence history entries (truncated to 500 characters each).
- **Automated Secret Redaction (`_redact_secrets`)**:
  Before transmission to Bedrock, text passes through pattern matching for:
  - Standard API keys and authorization tokens (`api-key`, `access-token`, `auth-token`)
  - AWS secret keys (`aws-secret-access-key`)
  - Provider tokens (`sk-...`, `ghp_...`, `glpat-...`, `xox...`)
  - Private key headers and password assignments
  - Matched secrets are replaced with `[REDACTED]`.

> [!WARNING]
> **Redaction Limitation**: Regex-based redaction is a defense-in-depth heuristic, not a mathematical guarantee. Obfuscated, non-standard, or novel secret formats might not match configured patterns. Never point Rootcause at repositories containing unencrypted plaintext production secrets.

---

## 6. Known Security Limitations

1. **No Kernel-Level Containerization**: Target project tests run with the privileges of the active operating system user.
2. **Third-Party Dependency Trust**: Any dependencies already installed in the active Python interpreter can execute arbitrary code during test execution.
3. **Prompt Injection Surface**: Target project file contents are fed to Nova Micro as evidence. While system instructions enforce strict JSON extraction and ignore embedded instructions, frontier LLMs remain susceptible to sophisticated indirect prompt injections.

---

## 7. Reporting a Vulnerability

If you discover a security issue or vulnerability in Rootcause, please open a private GitHub Security Advisory or report it directly to the maintainers rather than opening a public issue.
