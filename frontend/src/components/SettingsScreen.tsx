import { useState } from "react";

function Icon({
  name,
  className = "",
  style,
}: {
  name: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <span className={`material-symbols-outlined ${className}`} style={style} aria-hidden="true">
      {name}
    </span>
  );
}

export function SettingsScreen({
  onClose,
}: {
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"engine" | "safety" | "telemetry" | "workspaces" | "api">("engine");
  const [horizon, setHorizon] = useState(4);
  const [sandboxEnabled, setSandboxEnabled] = useState(true);
  const [verificationPolicy, setVerificationPolicy] = useState<"strict" | "balanced" | "exploratory">("strict");
  const [saved, setSaved] = useState(false);

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  }

  return (
    <div className="stitch-settings-page">
      {/* Page Header */}
      <div className="stitch-settings-topbar">
        <div className="stitch-settings-topbar-left">
          <button
            className="stitch-settings-back"
            type="button"
            onClick={onClose}
            aria-label="Back"
          >
            <Icon name="arrow_back" className="icon-18" />
          </button>
          <div>
            <div className="stitch-settings-title-row">
              <h1 className="stitch-settings-h1">Settings</h1>
              <span className="stitch-settings-version-badge">
                <span className="stitch-settings-version-dot" />
                v2.4.1-rc3
              </span>
            </div>
            <p className="stitch-settings-subtitle">
              Configure diagnostic engine parameters, local runner boundaries, and safety policies.
            </p>
          </div>
        </div>
        <div className="stitch-settings-topbar-actions">
          <div className="stitch-settings-config-path">
            <Icon name="terminal" className="icon-16" />
            <span>~/.rootcause/config.yaml</span>
            <span className="stitch-settings-synced">Synced</span>
          </div>
          <button className="stitch-settings-btn-reset" type="button" onClick={() => { setHorizon(4); setSandboxEnabled(true); }}>
            <Icon name="restart_alt" className="icon-18" />
            Reset Defaults
          </button>
          <button className={`stitch-settings-btn-save ${saved ? "stitch-settings-btn-save--saved" : ""}`} type="button" onClick={handleSave}>
            <Icon name={saved ? "check_circle" : "done_all"} className="icon-18" />
            {saved ? "Saved to YAML" : "Save Configuration"}
          </button>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="stitch-settings-tabbar">
        <nav className="stitch-settings-tabs" aria-label="Settings categories">
          {([
            { id: "engine", icon: "psychology", label: "Engine & Decider" },
            { id: "safety", icon: "shield", label: "Safety & Sandboxing" },
            { id: "telemetry", icon: "hub", label: "Telemetry & Bedrock" },
            { id: "workspaces", icon: "folder_special", label: "Local Workspaces" },
            { id: "api", icon: "key", label: "API & Integrations" },
          ] as { id: typeof activeTab; icon: string; label: string }[]).map(({ id, icon, label }) => (
            <button
              key={id}
              className={`stitch-settings-tab ${activeTab === id ? "stitch-settings-tab--active" : ""}`}
              type="button"
              onClick={() => setActiveTab(id)}
            >
              <Icon name={icon} className="icon-18" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Body: two-column grid */}
      <div className="stitch-settings-body">
        {/* Primary column */}
        <div className="stitch-settings-primary">

          {/* SECTION 01 — Decider 2B & Diagnostic Bounds */}
          {(activeTab === "engine") && (
            <>
              <section className="stitch-settings-section">
                <div className="stitch-settings-section-header">
                  <div className="stitch-settings-section-title-row">
                    <span className="stitch-section-num">01</span>
                    <h2 className="stitch-section-h2">Decider 2B &amp; Diagnostic Bounds</h2>
                  </div>
                  <span className="stitch-section-key">core.decider_v2</span>
                </div>

                {/* Step Horizon card */}
                <div className="stitch-card">
                  <div className="stitch-card-row">
                    <div className="stitch-card-info">
                      <span className="stitch-card-title">Diagnostic Step Horizon</span>
                      <p className="stitch-card-desc">
                        Maximum consecutive diagnostic steps Strands Decider 2B may evaluate before requiring verification or terminating.
                      </p>
                    </div>
                    <div className="stitch-stepper">
                      <button className="stitch-stepper-btn" type="button" onClick={() => setHorizon(h => Math.max(1, h - 1))} aria-label="Decrease">
                        <Icon name="remove" className="icon-16" />
                      </button>
                      <span className="stitch-stepper-val">{horizon}</span>
                      <button className="stitch-stepper-btn" type="button" onClick={() => setHorizon(h => Math.min(10, h + 1))} aria-label="Increase">
                        <Icon name="add" className="icon-16" />
                      </button>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="stitch-progress-wrap">
                    <div className="stitch-progress-track">
                      <div
                        className="stitch-progress-fill"
                        style={{ width: `${Math.max(10, ((horizon - 1) / 9) * 100)}%` }}
                      />
                    </div>
                    <div className="stitch-progress-labels">
                      <span>1 step (Rapid)</span>
                      <span className="stitch-progress-recommended">4 steps (Recommended)</span>
                      <span>10 steps (Exhaustive)</span>
                    </div>
                  </div>

                  <div className="stitch-info-callout">
                    <Icon name="info" className="icon-18" style={{ color: "var(--color-warning)", flexShrink: 0 }} />
                    <p>
                      Prevents runaway tool loops in circular dependency failures and runaway recursion traces. Default is auto-tuned for low token consumption.
                    </p>
                  </div>
                </div>

                {/* Verification Policy card */}
                <div className="stitch-card">
                  <div className="stitch-card-info" style={{ marginBottom: 16 }}>
                    <span className="stitch-card-title">Hypothesis Verification Policy</span>
                    <p className="stitch-card-desc">
                      Determines threshold of cryptographic and runtime evidence mandatory to surface a hypothesis as actionable root cause.
                    </p>
                  </div>
                  <div className="stitch-policy-grid">
                    {([
                      {
                        id: "strict" as const,
                        badge: "Strict",
                        badgeClass: "stitch-badge--success",
                        title: "Deterministic",
                        desc: "Requires reproducible local runtime check or AST proof before labeling root cause.",
                      },
                      {
                        id: "balanced" as const,
                        badge: "Balanced",
                        badgeClass: "stitch-badge--muted",
                        title: "Heuristic",
                        desc: "Accepts high-probability static indicators when runtime probes are isolated or mocked.",
                      },
                      {
                        id: "exploratory" as const,
                        badge: "Broad",
                        badgeClass: "stitch-badge--muted",
                        title: "Exploratory",
                        desc: "Logs all plausible causal paths. Surfacing speculative regressions alongside confirmed faults.",
                      },
                    ]).map(({ id, badge, badgeClass, title, desc }) => (
                      <label
                        key={id}
                        className={`stitch-policy-card ${verificationPolicy === id ? "stitch-policy-card--selected" : ""}`}
                        onClick={() => setVerificationPolicy(id)}
                      >
                        <input type="radio" name="verification_policy" value={id} checked={verificationPolicy === id} onChange={() => setVerificationPolicy(id)} className="sr-only" />
                        <div className="stitch-policy-card-top">
                          <span className={`stitch-badge ${badgeClass}`}>{badge}</span>
                          <span className={`stitch-radio-dot ${verificationPolicy === id ? "stitch-radio-dot--on" : ""}`}>
                            {verificationPolicy === id && <span className="stitch-radio-inner" />}
                          </span>
                        </div>
                        <span className="stitch-policy-title">{title}</span>
                        <p className="stitch-policy-desc">{desc}</p>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Automated Remediation Sandbox card */}
                <div className="stitch-card stitch-card--row">
                  <div className="stitch-card-info">
                    <div className="stitch-card-title-row">
                      <span className="stitch-card-title">Automated Remediation Sandbox</span>
                      <span className="stitch-badge stitch-badge--success">Active Safe Mode</span>
                    </div>
                    <p className="stitch-card-desc">
                      Execute candidate fixes inside an isolated subprocess with automatic state snapshots prior to user review.
                    </p>
                  </div>
                  <div className="stitch-toggle-group">
                    <label className="stitch-toggle-wrap">
                      <input type="checkbox" className="sr-only" checked={sandboxEnabled} onChange={e => setSandboxEnabled(e.target.checked)} id="toggle-sandbox" />
                      <div className={`stitch-toggle-track ${sandboxEnabled ? "stitch-toggle-track--on" : ""}`}>
                        <div className={`stitch-toggle-thumb ${sandboxEnabled ? "stitch-toggle-thumb--on" : ""}`} />
                      </div>
                    </label>
                    <span className="stitch-toggle-label">{sandboxEnabled ? "Enabled" : "Disabled"}</span>
                  </div>
                </div>
              </section>

              {/* SECTION 02 — Filesystem & Parsing Safeguards */}
              <section className="stitch-settings-section">
                <div className="stitch-settings-section-header">
                  <div className="stitch-settings-section-title-row">
                    <span className="stitch-section-num">02</span>
                    <h2 className="stitch-section-h2">Filesystem &amp; Parsing Safeguards</h2>
                  </div>
                  <span className="stitch-section-key">runner.limits</span>
                </div>

                <div className="stitch-card">
                  <div className="stitch-limits-grid">
                    <div className="stitch-limit-field">
                      <label className="stitch-limit-label" htmlFor="max-file-size">
                        <span>File Inspection Size Limit</span>
                        <span className="stitch-limit-unit">Bytes / MB</span>
                      </label>
                      <div className="stitch-limit-input-wrap">
                        <input className="stitch-limit-input" id="max-file-size" type="text" defaultValue="25 MB" />
                        <span className="stitch-limit-suffix">binary cap</span>
                      </div>
                      <p className="stitch-limit-desc">
                        Protects AST parser against unindexed model weight binaries like{" "}
                        <code className="stitch-inline-code">large_model_weights.py</code>.
                      </p>
                    </div>
                    <div className="stitch-limit-field">
                      <label className="stitch-limit-label" htmlFor="subprocess-timeout">
                        <span>Subprocess Probe Timeout</span>
                        <span className="stitch-limit-unit">Seconds (s)</span>
                      </label>
                      <div className="stitch-limit-input-wrap">
                        <input className="stitch-limit-input" id="subprocess-timeout" type="text" defaultValue="30s" />
                        <span className="stitch-limit-suffix">SIGKILL</span>
                      </div>
                      <p className="stitch-limit-desc">
                        Maximum execution allowance per diagnostic test probe before kernel execution abort.
                      </p>
                    </div>
                  </div>

                  {/* Ignored patterns textarea */}
                  <div className="stitch-patterns-wrap">
                    <div className="stitch-patterns-header">
                      <label className="stitch-patterns-label" htmlFor="ignored-patterns">Ignored Directory &amp; File Patterns</label>
                      <button className="stitch-patterns-reset" type="button">
                        <Icon name="history" className="icon-14" />
                        Reset .rootcauseignore
                      </button>
                    </div>
                    <div className="stitch-patterns-editor">
                      <textarea
                        className="stitch-patterns-textarea"
                        id="ignored-patterns"
                        rows={5}
                        defaultValue={".rootcauseignore\nnode_modules/\n.venv/\ndist/\nbuild/\n*.bin\n*.onnx\n.git/"}
                      />
                      <span className="stitch-patterns-count">8 patterns loaded</span>
                    </div>
                    <p className="stitch-limit-desc">Applied during static indexing, AST traversal, and symbolic execution scans.</p>
                  </div>
                </div>
              </section>

              {/* SECTION 03 — Reasoning Engine & Amazon Bedrock */}
              <section className="stitch-settings-section">
                <div className="stitch-settings-section-header">
                  <div className="stitch-settings-section-title-row">
                    <span className="stitch-section-num">03</span>
                    <h2 className="stitch-section-h2">Reasoning Engine &amp; Amazon Bedrock</h2>
                  </div>
                  <span className="stitch-section-key">telemetry.bedrock</span>
                </div>

                <div className="stitch-card">
                  {/* Bedrock provider row */}
                  <div className="stitch-bedrock-row">
                    <div className="stitch-bedrock-icon">
                      <Icon name="cloud_sync" className="icon-24" />
                    </div>
                    <div className="stitch-bedrock-info">
                      <div className="stitch-bedrock-name-row">
                        <span className="stitch-card-title">Bedrock Analysis Provider</span>
                        <span className="stitch-badge stitch-badge--success-xs">Active</span>
                      </div>
                      <span className="stitch-bedrock-model">anthropic.claude-3-5-sonnet-20241022-v2:0</span>
                    </div>
                    <div className="stitch-bedrock-region">
                      <span className="stitch-region-pill">us-east-1</span>
                      <span className="stitch-status-dot stitch-status-dot--green" />
                    </div>
                  </div>

                  {/* Fallback row */}
                  <div className="stitch-fallback-row">
                    <div>
                      <span className="stitch-card-title" style={{ fontSize: 14 }}>Fallback Decider Strategy</span>
                      <p className="stitch-card-desc">Fallback to local model if cloud inference latency spikes or credentials fail.</p>
                    </div>
                    <span className="stitch-threshold-pill">Threshold: 3500ms</span>
                  </div>

                  {/* Local model row */}
                  <div className="stitch-local-model-row">
                    <div className="stitch-local-model-left">
                      <Icon name="laptop_chromebook" className="icon-20" style={{ color: "var(--color-text-secondary)" }} />
                      <div>
                        <span className="stitch-local-model-name">Local Strands Decider 2B</span>
                        <span className="stitch-local-model-desc">On-device quantized heuristic runner</span>
                      </div>
                    </div>
                    <div className="stitch-local-model-status">
                      <span className="stitch-status-text--green">Engaged</span>
                      <span className="stitch-status-dot stitch-status-dot--green" />
                    </div>
                  </div>
                </div>
              </section>
            </>
          )}

          {activeTab !== "engine" && (
            <div className="stitch-card" style={{ padding: 40, textAlign: "center" }}>
              <Icon name={activeTab === "safety" ? "shield" : activeTab === "telemetry" ? "hub" : activeTab === "workspaces" ? "folder_special" : "key"} className="icon-20" style={{ color: "var(--color-text-muted)", display: "block", margin: "0 auto 12px" }} />
              <p style={{ color: "var(--color-text-muted)", fontSize: 14 }}>
                {activeTab === "safety" ? "Safety & Sandboxing" : activeTab === "telemetry" ? "Telemetry & Bedrock" : activeTab === "workspaces" ? "Local Workspaces" : "API & Integrations"} configuration coming soon.
              </p>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="stitch-settings-sidebar">
          {/* Engine Telemetry card */}
          <div className="stitch-sidebar-card">
            <div className="stitch-sidebar-card-header">
              <span className="stitch-sidebar-card-title">Engine Telemetry</span>
              <Icon name="query_stats" className="icon-18" style={{ color: "var(--color-text-muted)" }} />
            </div>

            {/* Memory ring + value */}
            <div className="stitch-telemetry-ring-row">
              <div className="stitch-ring-wrap">
                <svg className="stitch-ring-svg" viewBox="0 0 36 36">
                  <path className="stitch-ring-track" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeWidth="3.5" />
                  <path className="stitch-ring-fill" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeDasharray="68, 100" strokeLinecap="round" strokeWidth="3.5" />
                </svg>
                <span className="stitch-ring-label">68%</span>
              </div>
              <div>
                <span className="stitch-telemetry-mem-desc">Model Memory Footprint</span>
                <span className="stitch-telemetry-mem-val">1.36 GB / 2.00 GB</span>
                <span className="stitch-telemetry-quant">Quantization: Q4_K_M</span>
              </div>
            </div>

            {/* Metrics list */}
            <div className="stitch-metrics-list">
              {[
                { label: "Inference Latency (Local)", value: "18.4ms", highlight: false },
                { label: "Bedrock P95 Latency", value: "642ms", highlight: false },
                { label: "AST Index Cache Size", value: "4.8 MB", highlight: false },
                { label: "Decider Tooling Probes", value: "14 Available", highlight: true },
              ].map(({ label, value, highlight }) => (
                <div key={label} className="stitch-metric-row">
                  <span className="stitch-metric-label">{label}</span>
                  <span className={`stitch-metric-value ${highlight ? "stitch-metric-value--green" : ""}`}>{value}</span>
                </div>
              ))}
            </div>

            <button className="stitch-benchmark-btn" type="button">
              <Icon name="speed" className="icon-16" />
              Run Engine Benchmark
            </button>
          </div>

          {/* Environment Isolation card */}
          <div className="stitch-sidebar-card">
            <div className="stitch-sidebar-card-header">
              <span className="stitch-sidebar-card-title">Environment Isolation</span>
              <span className="stitch-badge stitch-badge--primary-sm">Local Native</span>
            </div>
            <p className="stitch-card-desc">
              Diagnoses are performed against your local POSIX workspace via subshell instrumentation.
            </p>
            <div className="stitch-env-fields">
              <div className="stitch-env-field">
                <span className="stitch-env-field-label">Default Interpreter</span>
                <span className="stitch-env-field-value">/opt/homebrew/bin/python3.11</span>
              </div>
              <div className="stitch-env-field">
                <span className="stitch-env-field-label">Temporary Diff Stash</span>
                <span className="stitch-env-field-value">~/.rootcause/cache/patches/</span>
              </div>
            </div>
            <div className="stitch-env-zero-out">
              <Icon name="lock" className="icon-16" style={{ color: "var(--color-success)" }} />
              <span>Zero outbound code transmission</span>
            </div>
          </div>

          {/* Configuration Payload card */}
          <div className="stitch-sidebar-card stitch-sidebar-card--low">
            <span className="stitch-sidebar-card-title" style={{ display: "block", marginBottom: 8 }}>Configuration Payload</span>
            <p className="stitch-card-desc">
              Share identical verification criteria and limits across your engineering squad via repository root.
            </p>
            <div className="stitch-payload-buttons">
              <button className="stitch-payload-btn" type="button">
                <Icon name="file_download" className="icon-16" />
                Export .yaml
              </button>
              <button className="stitch-payload-btn" type="button">
                <Icon name="file_upload" className="icon-16" />
                Import
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
