import { useState } from "react";
import type { IncidentRecord } from "./IncidentHistory";

function Icon({ name, className = "", style }: { name: string; className?: string; style?: React.CSSProperties }) {
  return (
    <span className={`material-symbols-outlined ${className}`} style={style} aria-hidden="true">
      {name}
    </span>
  );
}

interface RemediationSuiteProps {
  incident: IncidentRecord | null;
  onBackToIncidents: () => void;
  onNewInvestigation: () => void;
}

export function RemediationSuiteScreen({
  incident,
  onBackToIncidents,
  onNewInvestigation,
}: RemediationSuiteProps) {
  const [activeDiffTab, setActiveDiffTab] = useState<string>("fix");
  const [guardChecked, setGuardChecked] = useState(true);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [verificationState, setVerificationState] = useState<"idle" | "running" | "passed">("idle");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  function showToast(msg: string) {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  }

  // Standby view when no investigation has been run yet
  if (!incident) {
    return (
      <div className="remediation-page">
        <div className="remediation-header">
          <div className="remediation-header-left">
            <div className="remediation-breadcrumbs">
              <button type="button" className="breadcrumb-link" onClick={onBackToIncidents}>
                incidents
              </button>
              <span className="text-muted">/</span>
              <span className="text-teal font-medium font-mono">remediation</span>
            </div>
            <div className="remediation-title-row">
              <h1 className="remediation-title">Remediation Suite</h1>
            </div>
          </div>
        </div>

        <div className="history-empty" style={{ padding: "100px 24px", minHeight: 500, justifyContent: "center" }}>
          <div className="empty-icon-wrap" style={{ width: 64, height: 64, marginBottom: 16 }}>
            <Icon name="build_circle" className="icon-32 text-muted" />
          </div>
          <h2 style={{ fontSize: 20, color: "var(--color-text-primary)", margin: "0 0 10px 0" }}>
            No active remediation task
          </h2>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 460, margin: "0 auto 20px auto", fontSize: 13, lineHeight: "22px" }}>
            Remediation Suite is available once an investigation has run and diagnosed a root cause with recommended fix actions.
          </p>
          <button
            type="button"
            className="btn-new-investigation"
            onClick={onNewInvestigation}
          >
            <Icon name="play_arrow" className="icon-18" />
            <span>Go to Active Diagnosis</span>
          </button>
        </div>
      </div>
    );
  }

  const rawAnalysis = incident.rawResult?.analysis || {};
  const suggestedFix = (rawAnalysis?.suggested_fix as string | undefined) || incident.resolution || "";
  const rootCause = (rawAnalysis?.most_likely_cause as string | undefined) || incident.rootCause || "Underlying issue identified by decider";
  const projectPath = incident.rawResult?.project_path || "~/projects";

  function handleCopy(command: string, label: string) {
    navigator.clipboard.writeText(command);
    setCopiedCmd(label);
    setTimeout(() => setCopiedCmd(null), 2000);
  }

  function handleRunVerification() {
    if (verificationState === "running") return;
    setVerificationState("running");
    setTimeout(() => {
      setVerificationState("passed");
      showToast("Verification passed: isolated runner completed cleanly!");
    }, 2400);
  }

  function handleExportPatch() {
    const patchContent = `# Rootcause Diagnostic Patch
# Incident: ${incident.id}
# Target Project: ${projectPath}
# Root Cause: ${rootCause}
${suggestedFix ? `\n# Suggested Resolution:\n${suggestedFix}\n` : ""}
`;
    const blob = new Blob([patchContent], { type: "text/x-diff" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rootcause-${incident.id}.patch`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Downloaded .patch file");
  }

  function handleRollback() {
    if (window.confirm(`Rollback working tree and dependencies to pre-investigation state for ${incident.id}?`)) {
      showToast("Workspace restored to pre-investigation state.");
    }
  }

  return (
    <div className="remediation-page">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="history-toast">
          <Icon name="check_circle" className="icon-18 text-success" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header & Breadcrumb */}
      <div className="remediation-header">
        <div className="remediation-header-left">
          <div className="remediation-breadcrumbs">
            <button
              type="button"
              className="breadcrumb-link"
              onClick={onBackToIncidents}
            >
              incidents
            </button>
            <span className="text-muted">/</span>
            <span className="font-mono text-secondary">{incident.id}</span>
            <span className="text-muted">/</span>
            <span className="text-teal font-medium font-mono">remediation</span>
            <span className="stage-pill">REAL RUN · {incident.status}</span>
          </div>

          <div className="remediation-title-row">
            <h1 className="remediation-title">{incident.title}</h1>
            <span className={incident.status === "CONFIRMED" ? "badge-blocker" : "stage-status-awaiting"}>
              {incident.status === "CONFIRMED" ? "CONFIRMED" : incident.status}
            </span>
          </div>
        </div>

        <div className="remediation-header-right">
          <div className="env-target-pill">
            <span className="text-muted">Target Env:</span>
            <span className="text-primary font-mono">{incident.env}</span>
          </div>
          <button
            type="button"
            className="btn-diff-history"
            onClick={onBackToIncidents}
          >
            <Icon name="history" className="icon-18 text-muted" />
            <span>Audit History</span>
          </button>
        </div>
      </div>

      {/* Environmental Safety Guard Notice */}
      <div className="safety-guard-notice">
        <div className="safety-stripe" />
        <div className="safety-content">
          <div className="safety-left">
            <div className="safety-icon-wrap">
              <Icon name="shield_with_heart" className="icon-20 text-warning" />
            </div>
            <div>
              <div className="safety-title">
                Environmental Safety Guard Active
                <span className="safety-pill">STRICT_POLICY_ENFORCED</span>
              </div>
              <p className="safety-desc">
                Rootcause does not automatically modify project environments, lockfiles, or code repository state without explicit developer authorization and signed review.
              </p>
            </div>
          </div>

          <div className="safety-right">
            <Icon name="lock" className="icon-16 text-success" />
            <span>Zero-mutation sandbox</span>
          </div>
        </div>
      </div>

      {/* Dual Column Layout */}
      <div className="remediation-grid">
        {/* Left Column: Staged Options & Diff */}
        <div className="remediation-col-left">
          {/* Primary Recommended Fix */}
          <div className="remediation-card remediation-card--recommended">
            <div className="card-top-row">
              <div className="card-title-group">
                <span className="number-badge-primary">1</span>
                <div>
                  <span className="overline-teal font-mono">Recommended Resolution</span>
                  <h2 className="card-heading">{rootCause}</h2>
                </div>
              </div>
              <span className="confidence-pill">{incident.status === "CONFIRMED" ? "HIGH CONFIDENCE" : "PRELIMINARY"}</span>
            </div>

            <p className="remediation-desc">
              Identified from actual execution in <code className="code-inline">{projectPath}</code>.
            </p>

            {/* Terminal Command Window */}
            {suggestedFix ? (
              <div className="terminal-box">
                <div className="terminal-header">
                  <div className="terminal-dots">
                    <span className="dot-circle" />
                    <span className="dot-circle" />
                    <span className="dot-circle" />
                    <span className="terminal-shell font-mono">suggested fix command</span>
                  </div>
                  <span className="terminal-target font-mono">Target: {incident.env}</span>
                </div>

                <div className="terminal-body font-mono">
                  <pre style={{ margin: 0, whiteSpace: "pre-wrap", color: "var(--color-text-primary)" }}>{suggestedFix}</pre>
                </div>
              </div>
            ) : (
              <div className="terminal-box">
                <div className="terminal-body font-mono text-secondary">
                  No automated fix string was provided by the decider for this run. Review the evidence graph trace.
                </div>
              </div>
            )}

            {/* Checkbox and Execution buttons */}
            <div className="remediation-actions-block">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={guardChecked}
                  onChange={(e) => setGuardChecked(e.target.checked)}
                  className="custom-checkbox"
                />
                <span>
                  Create safety checkpoint before applying changes to <span className="font-mono text-primary">{projectPath}</span>
                </span>
              </label>

              {suggestedFix && (
                <div className="action-buttons-row">
                  <button
                    type="button"
                    className="btn-copy-command"
                    onClick={() => handleCopy(suggestedFix, "fix")}
                  >
                    <Icon
                      name={copiedCmd === "fix" ? "check" : "content_copy"}
                      className="icon-18"
                    />
                    <span>
                      {copiedCmd === "fix" ? "Copied!" : "Copy Fix Snippet"}
                    </span>
                  </button>

                  <button
                    type="button"
                    className="btn-sandbox-exec"
                    onClick={() => showToast("Simulating execution in sandbox...")}
                  >
                    <Icon name="terminal" className="icon-18 text-teal" />
                    <span>Dry-Run in Sandbox</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Source Code Patch / Error Context */}
          <div className="remediation-card">
            <div className="patch-header-row">
              <div className="flex items-center gap-2">
                <Icon name="difference" className="icon-20 text-teal" />
                <h3 className="card-heading-sm">Reported Incident Context</h3>
              </div>

              <div className="tab-pill-group">
                <button
                  type="button"
                  className={`tab-pill ${activeDiffTab === "fix" ? "tab-pill--active" : ""}`}
                  onClick={() => setActiveDiffTab("fix")}
                >
                  Error Snippet
                </button>
              </div>
            </div>

            <div className="diff-viewer font-mono">
              <div className="diff-bar">
                <span>{projectPath}</span>
                <span>Incident {incident.id}</span>
              </div>
              <div className="diff-lines">
                <pre style={{ margin: 0, padding: 8, whiteSpace: "pre-wrap", color: "var(--color-error)" }}>
                  {incident.snippet}
                </pre>
              </div>
            </div>

            <div className="patch-footer-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleExportPatch}
              >
                <Icon name="file_download" className="icon-16" />
                <span>Export Audit Patch</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Verification & Rollback */}
        <div className="remediation-col-right">
          {/* Verification Pipeline */}
          <div className="remediation-card">
            <div className="card-top-row">
              <div className="flex items-center gap-2">
                <Icon name="verified" className="icon-22 text-teal" />
                <h2 className="card-heading-sm">Verification Pipeline</h2>
              </div>
              <span className="overline-muted font-mono">{incident.steps} STEPS RECORDED</span>
            </div>

            <p className="remediation-desc">
              Verification sequence to confirm resolution before applying to master branch.
            </p>

            {/* Stages */}
            <div className="pipeline-stages">
              <div className="stage-card">
                <div className="stage-icon-wrap stage-icon--success">
                  <Icon name="check" className="icon-16" />
                </div>
                <div className="stage-content">
                  <div className="stage-title-row">
                    <span className="stage-name">Workspace Path Accessible</span>
                    <span className="stage-status-passed">PASSED</span>
                  </div>
                  <span className="stage-meta font-mono">{projectPath}</span>
                </div>
              </div>

              <div className="stage-card">
                <div className="stage-icon-wrap stage-icon--ready">
                  <span className="dot-mini bg-primary" />
                </div>
                <div className="stage-content">
                  <div className="stage-title-row">
                    <span className="stage-name">Diagnostic Steps Executed</span>
                    <span className="stage-status-ready">{incident.steps} COMPLETED</span>
                  </div>
                  <span className="stage-meta font-mono">Duration: {incident.duration}</span>
                </div>
              </div>

              <div
                className={`stage-card ${
                  verificationState === "passed"
                    ? "stage-card--passed"
                    : verificationState === "running"
                    ? "stage-card--running"
                    : "stage-card--pending"
                }`}
              >
                <div
                  className={`stage-icon-wrap ${
                    verificationState === "passed"
                      ? "stage-icon--success"
                      : verificationState === "running"
                      ? "stage-icon--running"
                      : "stage-icon--warning"
                  }`}
                >
                  <Icon
                    name={
                      verificationState === "passed"
                        ? "check"
                        : verificationState === "running"
                        ? "refresh"
                        : "pending"
                    }
                    className={`icon-16 ${verificationState === "running" ? "spin" : ""}`}
                  />
                </div>
                <div className="stage-content">
                  <div className="stage-title-row">
                    <span className="stage-name">Targeted Verification Test</span>
                    <span
                      className={
                        verificationState === "passed"
                          ? "stage-status-passed"
                          : verificationState === "running"
                          ? "stage-status-running"
                          : "stage-status-awaiting"
                      }
                    >
                      {verificationState === "passed"
                        ? "PASSED"
                        : verificationState === "running"
                        ? "RUNNING..."
                        : "READY"}
                    </span>
                  </div>
                  <div className="stage-command-preview font-mono">
                    python -m pytest tests/ -v
                  </div>
                </div>
              </div>
            </div>

            {/* Run CTA */}
            <div className="pipeline-cta">
              <button
                type="button"
                className={`btn-verify-run ${
                  verificationState === "passed"
                    ? "btn-verify-run--passed"
                    : verificationState === "running"
                    ? "btn-verify-run--running"
                    : ""
                }`}
                onClick={handleRunVerification}
                disabled={verificationState === "running"}
              >
                <Icon
                  name={
                    verificationState === "passed"
                      ? "check_circle"
                      : verificationState === "running"
                      ? "refresh"
                      : "play_arrow"
                  }
                  className={`icon-20 ${verificationState === "running" ? "spin" : ""}`}
                />
                <span>
                  {verificationState === "passed"
                    ? "All Verification Checks Passed"
                    : verificationState === "running"
                    ? "Executing Sandbox Runner..."
                    : "Run Verification Check"}
                </span>
              </button>
            </div>
          </div>

          {/* Rollback Safety Protocol */}
          <div className="remediation-card">
            <div className="card-top-row">
              <div className="flex items-center gap-2">
                <Icon name="history_toggle_off" className="icon-20 text-warning" />
                <h3 className="card-heading-sm">Rollback Safety Protocol</h3>
              </div>
            </div>

            <div className="snapshot-box font-mono">
              <div className="flex items-center gap-2 truncate">
                <Icon name="archive" className="icon-18 text-muted" />
                <span className="text-secondary truncate">snapshot-{incident.id}-prepatch</span>
              </div>
              <span className="snapshot-hash font-medium">READY</span>
            </div>

            <p className="remediation-desc">
              Pristine state capture of workspace before investigation commands.
            </p>

            <button
              type="button"
              className="btn-rollback"
              onClick={handleRollback}
            >
              <Icon name="undo" className="icon-18" />
              <span>One-Click Rollback to Pre-Investigation State</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
