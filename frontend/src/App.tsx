"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import "./index.css";
import { IncidentHistoryScreen, type IncidentRecord } from "./components/IncidentHistory";
import { EvidenceGraphScreen } from "./components/EvidenceGraph";
import { RemediationSuiteScreen } from "./components/RemediationSuite";

const API_BASE = "/api";
const STORAGE_KEY = "rootcause_incident_history";

function loadSavedIncidents(): IncidentRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export type NavigationTab = "diagnosis" | "history" | "graph" | "remediation";

// ─── Types ────────────────────────────────────────────────
interface HealthStatus {
  status: string;
  service: string;
  version: string;
  modules: Record<string, boolean>;
  decider_reachable: boolean;
  bedrock_configured: boolean;
}

interface HistoryStep {
  step: number;
  result: Record<string, unknown>;
}

interface InvestigationResult {
  project_path: string;
  reported_error: string;
  steps_completed: number;
  actions_executed: string[];
  evidence_history: string[];
  history: HistoryStep[];
  stop_reason: string;
  truncation_notice?: string | null;
  analysis: Record<string, unknown> | null;
  analysis_status?: string | null;
  analysis_error?: string | null;
}

interface ExpectedOutcome {
  scenario_id: string;
  failure_category: string;
  expected_evidence: string[];
  expected_diagnosis_category: string;
  suggested_corrective_action: string;
  supported: boolean;
  limitations: string[];
}

interface DemoScenario {
  id: string;
  name: string;
  category: string;
  description: string;
  fixture_dir: string;
  project_path: string;
  error: string;
  expected_outcome: ExpectedOutcome;
}

interface ScenarioListResponse {
  scenarios: DemoScenario[];
}

type AppScreen = "idle" | "investigating" | "results" | "error";

interface AppState {
  healthStatus: "idle" | "checking" | "healthy" | "unhealthy";
  health: HealthStatus | null;
  healthError: string | null;
  screen: AppScreen;
  result: InvestigationResult | null;
  submitError: string | null;
  elapsedSeconds: number;
  investigationId: string | null;
}

const INITIAL_STATE: AppState = {
  healthStatus: "idle",
  health: null,
  healthError: null,
  screen: "idle",
  result: null,
  submitError: null,
  elapsedSeconds: 0,
  investigationId: null,
};

const SAMPLE_TRACEBACK = `Traceback (most recent call last):
  File "app/main.py", line 14, in <module>
    from app.database import engine, Base
  File "app/database.py", line 4, in <module>
    from sqlalchemy.dialects.postgresql import psycopg2
  File "venv/lib/python3.11/site-packages/sqlalchemy/dialects/postgresql/__init__.py", line 12, in <module>
    from . import psycopg2  # noqa
  File "venv/lib/python3.11/site-packages/sqlalchemy/dialects/postgresql/psycopg2.py", line 748, in <module>
    from ...connectors.asyncio import AsyncAdapt_dbapi_connection
  File "venv/lib/python3.11/site-packages/sqlalchemy/connectors/asyncio.py", line 14, in <module>
    import psycopg
ModuleNotFoundError: No module named 'psycopg'`;

// ─── Icon component ───────────────────────────────────────
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

// ─── Shared: Top Navigation Bar ──────────────────────────
function TopNav({
  health,
  healthStatus,
  healthError,
  projectPath,
}: {
  health: HealthStatus | null;
  healthStatus: string;
  healthError: string | null;
  projectPath: string;
}) {
  const deciderReady = health?.decider_reachable;
  const bedrockOk = health?.bedrock_configured;
  const allOk = healthStatus === "healthy";
  const isUnhealthy = healthStatus === "unhealthy";

  return (
    <header className="topnav" role="banner">
      {/* Brand */}
      <div className="topnav-brand">
        <div className="topnav-logo">
          <img src="/Rootcause_Logo.svg" alt="Rootcause" className="topnav-logo-mark" />
          <span className="topnav-wordmark">Rootcause</span>
        </div>
      </div>

      {/* Workspace indicator */}
      {projectPath && (
        <div className="topnav-workspace" aria-label="Current workspace">
          <span className="topnav-workspace-muted">Workspace:</span>
          <span className="topnav-workspace-path">{projectPath || "~/projects"}</span>
          <span className="topnav-workspace-sep">|</span>
          <span className="topnav-workspace-muted">branch:</span>
          <span className="topnav-workspace-branch">main</span>
        </div>
      )}

      {/* Right controls */}
      <div className="topnav-right">
        {/* System status pill */}
        <div
          className={`topnav-status${allOk ? " topnav-status--healthy" : isUnhealthy ? " topnav-status--unhealthy" : " topnav-status--checking"}`}
          role="status"
          aria-label="System health status"
        >
          <span
            className={`status-dot${allOk ? " status-dot--pulse" : ""}`}
            style={{ color: allOk ? "var(--color-success)" : isUnhealthy ? "var(--color-error)" : "var(--color-text-muted)" }}
          />
          <span
            className={`topnav-status-label${allOk ? " topnav-status-label--healthy" : isUnhealthy ? " topnav-status-label--unhealthy" : " topnav-status-label--checking"}`}
          >
            {allOk
              ? "Engine Ready"
              : isUnhealthy
              ? "API Unhealthy"
              : "Checking..."}
          </span>

          {/* Hover dropdown */}
          <div className="status-dropdown" role="tooltip">
            <div className="status-dropdown-title">Service Telemetry</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <div className="status-dropdown-row">
                <span className="status-dropdown-service">FastAPI</span>
                <span className={`status-dropdown-value ${allOk ? "status-dropdown-value--ok" : "status-dropdown-value--error"}`}>
                  {allOk ? "Connected" : isUnhealthy ? "Unreachable" : "—"}
                </span>
              </div>
              <div className="status-dropdown-row">
                <span className="status-dropdown-service">Strands Decider 2B</span>
                <span className={`status-dropdown-value ${deciderReady ? "status-dropdown-value--primary" : "status-dropdown-value--warn"}`}>
                  {deciderReady === true ? "Ready" : deciderReady === false ? "Unreachable" : "—"}
                </span>
              </div>
              <div className="status-dropdown-row">
                <span className="status-dropdown-service">Amazon Bedrock</span>
                <span className={`status-dropdown-value ${bedrockOk ? "status-dropdown-value--ok" : "status-dropdown-value--warn"}`}>
                  {bedrockOk === true ? "Available" : bedrockOk === false ? "Not configured" : "—"}
                </span>
              </div>
              {healthError && (
                <div className="status-dropdown-row" style={{ marginTop: 4 }}>
                  <span style={{ fontSize: 11, color: "var(--color-error)", fontFamily: "var(--font-mono)" }}>
                    {healthError}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Docs */}
        <a className="topnav-docs" href="#" aria-label="Documentation (placeholder)">Docs</a>

        {/* Settings */}
        <button className="topnav-icon-btn" aria-label="Settings (placeholder)" type="button">
          <Icon name="settings" className="icon-20" />
        </button>

        {/* Profile */}
        <div className="topnav-avatar" aria-label="User profile">
          <Icon name="person" className="icon-18" style={{ color: "var(--color-text-on-primary)" }} />
        </div>
      </div>
    </header>
  );
}

// ─── Shared: Sidebar ─────────────────────────────────────
function Sidebar({
  projectPath,
  health,
  activeTab,
  onSelectTab,
}: {
  projectPath: string;
  health: HealthStatus | null;
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
}) {
  const projectName = projectPath
    ? projectPath.split(/[/\\]/).filter(Boolean).pop() || projectPath
    : "—";
  const deciderVersion = "v2.4.1";

  return (
    <aside className="sidebar" aria-label="Diagnostics navigation">
      <div className="sidebar-top">
        <span className="sidebar-section-label">Diagnostics Engine</span>
        <nav className="sidebar-nav" aria-label="Main navigation">
          <button
            type="button"
            className={`sidebar-nav-item ${activeTab === "diagnosis" ? "sidebar-nav-item--active" : ""}`}
            onClick={() => onSelectTab("diagnosis")}
            aria-current={activeTab === "diagnosis" ? "page" : undefined}
          >
            <Icon name="biotech" className="icon-18" />
            <span>Active Diagnosis</span>
          </button>
          <button
            type="button"
            className={`sidebar-nav-item ${activeTab === "history" ? "sidebar-nav-item--active" : ""}`}
            onClick={() => onSelectTab("history")}
            aria-current={activeTab === "history" ? "page" : undefined}
          >
            <Icon name="history" className="icon-18" />
            <span>Incident History</span>
          </button>
          <button
            type="button"
            className={`sidebar-nav-item ${activeTab === "graph" ? "sidebar-nav-item--active" : ""}`}
            onClick={() => onSelectTab("graph")}
            aria-current={activeTab === "graph" ? "page" : undefined}
          >
            <Icon name="schema" className="icon-18" />
            <span>Evidence Graph</span>
          </button>
          <button
            type="button"
            className={`sidebar-nav-item ${activeTab === "remediation" ? "sidebar-nav-item--active" : ""}`}
            onClick={() => onSelectTab("remediation")}
            aria-current={activeTab === "remediation" ? "page" : undefined}
          >
            <Icon name="build_circle" className="icon-18" />
            <span>Remediation Suite</span>
          </button>
        </nav>

        {projectPath && (
          <div className="sidebar-workspace">
            <div className="sidebar-workspace-label">Target Workspace</div>
            <div className="sidebar-workspace-card">
              <div className="sidebar-workspace-name" title={projectPath}>{projectName}</div>
              <div className="sidebar-workspace-meta">
                <span className="dot-success" />
                <span>FastAPI Project</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        <span>Decider {deciderVersion}</span>
        <span className={`sidebar-footer-status ${health?.decider_reachable ? "" : "status-dropdown-value--warn"}`}
              style={{ color: health?.decider_reachable ? "var(--color-primary)" : "var(--color-warning)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
          {health?.decider_reachable ? "Online" : health === null ? "—" : "Offline"}
        </span>
      </div>
    </aside>
  );
}

// ─── Screen A: Main Workspace Form ───────────────────────
function WorkspaceScreen({
  projectPath,
  setProjectPath,
  errorText,
  setErrorText,
  maxSteps,
  setMaxSteps,
  healthStatus,
  investigating,
  submitError,
  onSubmit,
  onReset,
  demoScenarios,
  selectedDemoScenario,
  onSelectDemoScenario,
  demoScenariosLoading,
  demoScenariosError,
}: {
  projectPath: string;
  setProjectPath: (v: string) => void;
  errorText: string;
  setErrorText: (v: string) => void;
  maxSteps: number;
  setMaxSteps: (v: number) => void;
  healthStatus: string;
  investigating: boolean;
  submitError: string | null;
  onSubmit: (e: React.FormEvent) => void;
  onReset: () => void;
  demoScenarios: DemoScenario[];
  selectedDemoScenario: DemoScenario | null;
  onSelectDemoScenario: (s: DemoScenario | null) => void;
  demoScenariosLoading: boolean;
  demoScenariosError: string | null;
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [charCount, setCharCount] = useState({ chars: 0, lines: 0 });
  const [dryRun, setDryRun] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const browseInputRef = useRef<HTMLInputElement>(null);
  const pathTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const errorTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const PATH_PLACEHOLDERS = [
    "E:\\Projects\\my-app or /home/user/my-app",
    "C:\\Users\\you\\my-react-app",
    "/opt/rootcause/my-service",
    "~/projects/backend-api",
  ];
  const ERROR_PLACEHOLDERS = [
    "Paste Python tracebacks, exception logs, or terminal error output here (raw stdout/stderr supported)...",
    "Include full stack trace with file names and line numbers for better accuracy.",
    "Paste a JavaScript/TypeScript error from console or browser DevTools.",
    "Paste a Java stack trace or exception log from your server logs.",
  ];
  const [pathPlaceholder, setPathPlaceholder] = useState(PATH_PLACEHOLDERS[0]);
  const [errorPlaceholder, setErrorPlaceholder] = useState(ERROR_PLACEHOLDERS[0]);

  const CYCLE_MS = 5000;

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const val = e.target.value;
    setErrorText(val);
    setCharCount({ chars: val.length, lines: val ? val.split("\n").length : 0 });
  }

  function loadSampleTraceback() {
    setErrorText(SAMPLE_TRACEBACK);
    setCharCount({
      chars: SAMPLE_TRACEBACK.length,
      lines: SAMPLE_TRACEBACK.split("\n").length,
    });
    textareaRef.current?.focus();
  }

  function handleBrowse() {
    const el = browseInputRef.current;
    if (!el) return;
    el.setAttribute("webkitdirectory", "");
    el.setAttribute("directory", "");
    el.click();
  }

  function handleBrowseChange(e: React.ChangeEvent<HTMLInputElement>) {
    // Browser security prevents reading a folder's absolute path, so we only
    // open the native picker here; the user types (or pastes) the path manually.
    if (browseInputRef.current) browseInputRef.current.value = "";
  }

  function handleDemoScenarioChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value;
    if (!id) {
      onSelectDemoScenario(null);
      setProjectPath("");
      setErrorText("");
      setCharCount({ chars: 0, lines: 0 });
      textareaRef.current?.focus();
      return;
    }
    const scenario = demoScenarios.find((s) => s.id === id);
    if (!scenario) return;
    onSelectDemoScenario(scenario);
    setProjectPath(scenario.project_path);
    setErrorText(scenario.error);
    setCharCount({
      chars: scenario.error.length,
      lines: scenario.error.split("\n").length,
    });
    textareaRef.current?.focus();
  }

  // Independent placeholder cycles — each field scrolls through its own list
  useEffect(() => {
    let pi = 0;
    pathTimer.current = setInterval(() => {
      pi = (pi + 1) % PATH_PLACEHOLDERS.length;
      setPathPlaceholder(PATH_PLACEHOLDERS[pi]);
    }, CYCLE_MS);
    return () => {
      if (pathTimer.current) clearInterval(pathTimer.current);
    };
  }, []);

  useEffect(() => {
    let ei = 0;
    errorTimer.current = setInterval(() => {
      ei = (ei + 1) % ERROR_PLACEHOLDERS.length;
      setErrorPlaceholder(ERROR_PLACEHOLDERS[ei]);
    }, CYCLE_MS);
    return () => {
      if (errorTimer.current) clearInterval(errorTimer.current);
    };
  }, []);

  const isReady = healthStatus === "healthy" && !investigating;

  return (
    <div className="workspace-page">
      <div className="ambient-glow" aria-hidden="true" />

      {/* Hero */}
      <header className="workspace-hero">
        <h1 className="hero-h1">
          Find the cause.{" "}
          <span className="gradient-text">Fix the issue.</span>
        </h1>
        <p className="hero-description">
          Give Rootcause your project path and the error you're seeing. It will
          investigate the evidence and recommend the most likely fix.
        </p>
      </header>

      {/* Form card */}
      <section className="form-card" aria-label="Investigation form">
        <form className="form-body" onSubmit={onSubmit} noValidate>
          {/* Error banner */}
          {submitError && (
            <div className="form-error-banner" role="alert" style={{ marginBottom: 16 }}>
              <Icon name="error_outline" className="icon-20" style={{ color: "var(--color-error)", flexShrink: 0 }} />
              <div>
                <h4>Error</h4>
                <p>{submitError}</p>
              </div>
            </div>
          )}

          {/* Field 1: Project Directory */}
          <div className="form-field">
            <div className="form-field-header">
              <label className="form-label" htmlFor="project-path-input">
                <Icon name="folder_open" className="icon-20" style={{ color: "var(--color-primary)" }} />
                <span>Project Directory</span>
                <span className="field-tip" data-tip="Path to the local project directory accessible to the Rootcause backend.">
                  <Icon name="info" className="icon-14" style={{ color: "var(--color-text-muted)" }} />
                </span>
              </label>
            </div>
            <div className="input-wrap">
              <button
                className="form-input-browse"
                type="button"
                title="Browse"
                aria-label="Browse for project directory"
                onClick={handleBrowse}
                disabled={investigating}
              >
                <Icon name="folder" className="icon-16" style={{ flexShrink: 0 }} />
              </button>
              <input
                id="project-path-input"
                className="form-input"
                type="text"
                placeholder={pathPlaceholder}
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                disabled={investigating}
                autoComplete="off"
                spellCheck="false"
              />
              <input
                ref={browseInputRef}
                type="file"
                style={{ display: "none" }}
                onChange={handleBrowseChange}
              />
              {demoScenarios.length > 0 && (
                <button
                  className={`demo-btn ${selectedDemoScenario ? "demo-btn--active" : ""}`}
                  type="button"
                  title={selectedDemoScenario ? `Clear demo scenario: ${selectedDemoScenario.name}` : "Load a reproducible demo scenario"}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!selectedDemoScenario) {
                      const first = demoScenarios[0];
                      if (first) {
                        onSelectDemoScenario(first);
                        setProjectPath(first.project_path);
                        setErrorText(first.error);
                        setCharCount({ chars: first.error.length, lines: first.error.split("\n").length });
                        textareaRef.current?.focus();
                      }
                    } else {
                      handleDemoScenarioChange({ target: { value: "" } } as React.ChangeEvent<HTMLSelectElement>);
                    }
                  }}
                  disabled={investigating || demoScenariosLoading}
                >
                  {selectedDemoScenario ? "Change demo" : "Demo scenario"}
                </button>
              )}
              {demoScenarios.length > 0 && (
                <select
                  className="demo-select"
                  value={selectedDemoScenario ? selectedDemoScenario.id : ""}
                  onChange={handleDemoScenarioChange}
                  disabled={investigating || demoScenariosLoading}
                >
                  <option value="">Manual input — none selected</option>
                  {demoScenarios.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              )}
            </div>
            {selectedDemoScenario && (
              <p className="form-hint">
                <Icon name="info" className="icon-16" style={{ flexShrink: 0 }} />
                Loaded demo: <strong>{selectedDemoScenario.name}</strong> ({selectedDemoScenario.category}). Review the inputs, then investigate.
              </p>
            )}
          </div>
          {/* Field 2: Error input */}
          <div className="form-field">
            <div className="form-field-header">
              <label className="form-label" htmlFor="error-traceback-input">
                <Icon name="error_outline" className="icon-20" style={{ color: "var(--color-error)" }} />
                <span>Error Details</span>
              </label>
              <button
                className="sample-btn"
                type="button"
                onClick={loadSampleTraceback}
                disabled={investigating}
              >
                <Icon name="bolt" className="icon-16" />
                <span>Load sample traceback: ModuleNotFoundError (psycopg)</span>
              </button>
            </div>
            <div className="textarea-wrap">
              <textarea
                id="error-traceback-input"
                ref={textareaRef}
                className="form-textarea"
                placeholder={errorPlaceholder}
                value={errorText}
                onChange={handleTextareaChange}
                disabled={investigating}
                rows={7}
                spellCheck="false"
              />
              <span className="textarea-counter" aria-live="polite">
                {charCount.chars} chars • {charCount.lines} lines
              </span>
            </div>
          </div>

          {/* Advanced settings accordion */}
          <div className="advanced-toggle">
            <button
              className="advanced-toggle-btn"
              type="button"
              onClick={() => setAdvancedOpen(!advancedOpen)}
              aria-expanded={advancedOpen}
              id="advanced-toggle-btn"
            >
              <div className="advanced-toggle-inner">
                <Icon name="tune" className="icon-18" style={{ color: "var(--color-primary)" }} />
                <span>Advanced investigation settings</span>
              </div>
              <Icon
                name="expand_more"
                className={`advanced-chevron${advancedOpen ? " advanced-chevron--open" : ""}`}
              />
            </button>

            <div
              className={`advanced-drawer${advancedOpen ? " advanced-drawer--open" : ""}`}
              aria-hidden={!advancedOpen}
            >
              {/* Max steps slider */}
              <div className="advanced-setting-card">
                <div className="advanced-setting-header">
                  <div>
                    <div className="advanced-setting-title">
                      Maximum diagnostic steps:{" "}
                      <span className="advanced-setting-value">
                        {maxSteps}{maxSteps === 3 ? " (default)" : ""}
                      </span>
                    </div>
                    <div className="advanced-setting-desc">
                      Rootcause uses a bounded investigation with Strands Decider 2B to avoid unnecessary tool execution.
                    </div>
                  </div>
                  <input
                    className="steps-slider"
                    type="range"
                    min={1}
                    max={10}
                    value={maxSteps}
                    onChange={(e) => setMaxSteps(parseInt(e.target.value, 10))}
                    disabled={investigating}
                    aria-label={`Maximum diagnostic steps: ${maxSteps}`}
                  />
                </div>
              </div>

              {/* Dry-run toggle */}
              <div className="advanced-setting-card">
                <div className="advanced-setting-header" style={{ flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <div className="advanced-setting-title">Targeted dry-run check</div>
                    <div className="advanced-setting-desc">Run targeted dry-run check before recommending patch</div>
                  </div>
                  <label className="toggle-switch" aria-label="Enable targeted dry-run check">
                    <input
                      type="checkbox"
                      checked={dryRun}
                      onChange={(e) => setDryRun(e.target.checked)}
                      disabled={investigating}
                    />
                    <div className="toggle-track">
                      <div className="toggle-thumb" />
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="form-actions">
            <div className="form-actions-row">
              <button
                className="btn-investigate"
                type="submit"
                disabled={!isReady}
                aria-label="Start investigating the error"
              >
                <Icon name={investigating ? "autorenew" : "radar"} className={`btn-investigate-icon${investigating ? " spin-icon" : ""}`} />
                <span>{investigating ? "Orchestrating Strands Decider 2B…" : "Investigate error"}</span>
              </button>
              <button
                className="btn-reset"
                type="button"
                onClick={onReset}
                disabled={investigating}
                aria-label="Reset form"
              >
                <Icon name="restart_alt" className="icon-18" />
                <span>Reset form</span>
              </button>
            </div>
            <div className="form-assurance">
              <span>
                Diagnostics are evidence-driven. Rootcause does not automatically modify your source files without explicit confirmation.
              </span>
            </div>
            {healthStatus === "unhealthy" && (
              <p style={{ textAlign: "center", color: "var(--color-error)", fontSize: 13, fontFamily: "var(--font-mono)" }}>
                API is unreachable. Please ensure the backend is running.
              </p>
            )}
            {healthStatus === "checking" && (
              <p style={{ textAlign: "center", color: "var(--color-text-muted)", fontSize: 13, fontFamily: "var(--font-mono)" }}>
                Checking API health…
              </p>
            )}
          </div>
        </form>
      </section>

      {/* Feature cards */}
      <section className="feature-grid" aria-label="Platform capabilities">
        <div className="feature-card">
          <div className="feature-icon feature-icon--success" aria-hidden="true">
            <Icon name="science" className="icon-22" />
          </div>
          <div>
            <h2 className="feature-title">Evidence-First Analysis</h2>
            <p className="feature-desc">
              Distinguishes verified ground-truth tests from speculative hypotheses. Every conclusion cites concrete workspace logs and file checks.
            </p>
          </div>
        </div>
        <div className="feature-card">
          <div className="feature-icon feature-icon--info" aria-hidden="true">
            <Icon name="hub" className="icon-22" />
          </div>
          <div>
            <h2 className="feature-title">Decider 2B Orchestration</h2>
            <p className="feature-desc">
              Selects the next targeted diagnostic step strictly based on real workspace observations, bypassing generic chat loops.
            </p>
          </div>
        </div>
        <div className="feature-card">
          <div className="feature-icon feature-icon--primary" aria-hidden="true">
            <Icon name="precision_manufacturing" className="icon-22" />
          </div>
          <div>
            <h2 className="feature-title">Single Actionable Fix</h2>
            <p className="feature-desc">
              Get one high-confidence, verified patch or dependency command ready to apply, rather than endless speculative code snippets.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

// ─── Screen B: Investigation In Progress ─────────────────
function InvestigatingScreen({
  projectPath,
  errorText,
  elapsedSeconds,
}: {
  projectPath: string;
  errorText: string;
  elapsedSeconds: number;
}) {
  const [traceOpen, setTraceOpen] = useState(false);
  const elapsedDisplay = `${Math.floor(elapsedSeconds / 60).toString().padStart(2, "0")}:${(elapsedSeconds % 60).toString().padStart(2, "0")}s`;

  // Derive a short error summary for display
  const errorFirstLine = errorText.split("\n").find((l) => l.trim().length > 0) || errorText;
  const shortError = errorFirstLine.length > 64 ? errorFirstLine.slice(0, 64) + "…" : errorFirstLine;

  return (
    <div className="investigation-page">
      <div
        className="ambient-glow"
        aria-hidden="true"
        style={{ opacity: 0.3 }}
      />

      {/* Context card — shows submitted params */}
      <div className="inv-context-card">
        <div className="inv-context-row">
          <div className="inv-context-left">
            {projectPath && (
              <div className="inv-path-pill">
                <Icon name="folder_open" className="icon-16" style={{ color: "var(--color-text-muted)" }} />
                <span className="inv-path-text">{projectPath}</span>
              </div>
            )}
            <span style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)", fontSize: 13 }}>/</span>
            <div className="inv-error-pill">
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-error)", flexShrink: 0, display: "inline-block" }} />
              <span className="inv-error-label">Exception</span>
              <code className="inv-error-text">{shortError}</code>
            </div>
          </div>
          <div className="inv-context-right">
            <div className="agent-active-badge">
              <span className="agent-dot" />
              <span>Agent Active</span>
            </div>
            <div
              className="btn-cancel"
              role="button"
              aria-label="Cancellation is not available while investigation is running synchronously"
              title="Investigation is running synchronously. Cancel is not available."
              style={{ opacity: 0.5, cursor: "not-allowed" }}
            >
              <Icon name="close" className="icon-16" />
              <span>Cancel investigation</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main investigation card */}
      <div className="inv-main-card">
        {/* Status header */}
        <div className="inv-status-header">
          <div className="inv-status-left">
            <div className="inv-spinner-wrap" aria-hidden="true">
              <svg className="inv-spinner" viewBox="0 0 40 40" fill="none">
                <circle className="opacity-15" cx="20" cy="20" r="16" stroke="currentColor" strokeWidth="2.5" style={{ opacity: 0.15 }} />
                <path d="M36 20C36 11.1634 28.8366 4 20 4" stroke="currentColor" strokeLinecap="round" strokeWidth="2.5" />
              </svg>
              <Icon name="biotech" className="inv-spinner-icon" />
            </div>
            <div>
              <h1 className="inv-title">Investigating your error</h1>
              <p className="inv-desc">
                Collecting evidence to identify the most likely cause. Strands Decider 2B evaluating next diagnostic action.
              </p>
            </div>
          </div>

          <div className="inv-engine-pill" aria-label="Engine dispatch info">
            <span className="inv-engine-label">Engine Dispatch</span>
            <div className="inv-engine-value">
              <Icon name="psychology" className="icon-14" />
              <span>Strands Decider 2B</span>
            </div>
          </div>
        </div>

        {/* Progress */}
        <div className="inv-progress-section" aria-label="Investigation progress">
          <div className="inv-progress-header">
            <div className="inv-phase-left">
              <span className="inv-phase-label">Investigating</span>
              <span className="inv-phase-sep">•</span>
              <span className="inv-phase-desc">Running diagnostic checks…</span>
            </div>
            <span className="inv-elapsed" aria-live="polite">Elapsed: {elapsedDisplay}</span>
          </div>
          <div
            className="inv-progress-pills"
            style={{ gridTemplateColumns: "1fr" }}
            aria-label="Indeterminate progress — exact step count unavailable"
          >
            <div
              className="progress-pill progress-pill--indeterminate"
              style={{
                background: "linear-gradient(90deg, var(--color-primary) 0%, transparent 100%)",
                animation: "progressSweep 1.8s ease-in-out infinite",
              }}
            />
          </div>
          <style>{`
            @keyframes progressSweep {
              0% { background-position: -100% 0; }
              100% { background-position: 200% 0; }
            }
          `}</style>
        </div>

        {/* Timeline */}
        <div className="inv-timeline-section" aria-label="Diagnostic timeline">
          <div className="inv-timeline-header">
            <h2 className="inv-timeline-title">Diagnostic Timeline</h2>
            <span className="inv-timeline-count">Running…</span>
          </div>
          <div className="timeline-list">
            {/* Active step placeholder */}
            <div className="timeline-item timeline-item--active">
              <div className="timeline-item-row">
                <div className="timeline-item-left">
                  <span className="timeline-status-badge timeline-status-badge--active">
                    <span className="timeline-active-dot" aria-hidden="true" />
                    <span>In progress</span>
                  </span>
                  <div>
                    <h3 className="timeline-item-title">Executing diagnostic steps</h3>
                    <div className="timeline-running">
                      <Icon name="refresh" className="icon-16 spin-icon" style={{ color: "var(--color-primary)" }} />
                      <span>Strands Decider 2B selecting and executing tools…</span>
                    </div>
                  </div>
                </div>
                <span className="timeline-item-time timeline-item-time--active">active</span>
              </div>
            </div>
            {/* Queued placeholder */}
            <div className="timeline-item timeline-item--queued">
              <div className="timeline-item-row">
                <div className="timeline-item-left">
                  <span className="timeline-status-badge timeline-status-badge--queued">
                    <Icon name="hourglass_empty" className="icon-14" />
                    <span>Queued</span>
                  </span>
                  <div>
                    <h3 className="timeline-item-title timeline-item-title--queued">Evaluating collected evidence &amp; synthesizing root cause</h3>
                    <p className="timeline-item-desc timeline-item-desc--queued">Awaiting completion of diagnostic steps</p>
                  </div>
                </div>
                <span className="timeline-item-time">—</span>
              </div>
            </div>
          </div>
        </div>

        {/* Decider trace disclosure */}
        <div className="trace-disclosure">
          <button
            className="trace-toggle-btn"
            type="button"
            onClick={() => setTraceOpen(!traceOpen)}
            aria-expanded={traceOpen}
          >
            <div className="trace-toggle-left">
              <Icon name="terminal" className="icon-18" style={{ color: "var(--color-primary)" }} />
              <span className="trace-toggle-title">Diagnostic activity &amp; Decider trace</span>
              <span className="trace-count-badge">Live</span>
            </div>
            <div className="trace-toggle-right">
              <span>{traceOpen ? "Collapse" : "Expand"}</span>
              <Icon name="expand_more" className={`trace-chevron${traceOpen ? " trace-chevron--open" : ""}`} />
            </div>
          </button>
          <div className={`trace-content${traceOpen ? "" : " trace-content--hidden"}`} aria-hidden={!traceOpen}>
            <div className="trace-block">
              <div className="trace-block-header">
                <span className="text-label-sm" style={{ textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Investigation in progress
                </span>
                <span className="trace-block-status--primary" style={{ color: "var(--color-primary)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
                  Running
                </span>
              </div>
              <div className="trace-pre" style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
                Diagnostic trace will appear here when the investigation completes.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Screen C: Results (success or error) ────────────────
function ResultsScreen({
  result,
  onReset,
  onViewEvidenceGraph,
  onRemediate,
}: {
  result: InvestigationResult;
  onReset: () => void;
  onViewEvidenceGraph?: () => void;
  onRemediate?: () => void;
}) {
  const [traceOpen, setTraceOpen] = useState(true);
  const [copied, setCopied] = useState(false);
  const traceRef = useRef<HTMLElement>(null);

  const analysis = result.analysis;
  const analysisStatus = analysis?.["_analysis_status"] as string | undefined;
  const analysisError = analysis?.["_analysis_error"] as string | undefined;
  const analysisOk = analysisStatus === "success" || (analysis && !analysisStatus);
  const mostLikelyCause = analysis?.["most_likely_cause"] as string | null | undefined;
  const suggestedFix = analysis?.["suggested_fix"] as string | null | undefined;
  const confirmedObs = (analysis?.["confirmed_observations"] as string[] | undefined) ?? [];
  const altExplanations = (analysis?.["alternative_explanations"] as string[] | undefined) ?? [];
  const remainingUncertainty = (analysis?.["remaining_uncertainty"] as string[] | undefined) ?? [];
  const recommendedNextStep = analysis?.["recommended_next_step"] as string | null | undefined;
  const evidenceSufficient = analysis?.["evidence_sufficient"] as boolean | undefined;

  const stopReason = result.stop_reason;
  const isMaxSteps = stopReason === "maximum_steps_reached";
  const investigationId = `run_${Math.random().toString(36).slice(2, 10)}`;

  // Build a traceback from the history
  const traceLines: string[] = result.history.map((step, i) => {
    const res = step.result as Record<string, unknown>;
    const action = String(res.action ?? "unknown");
    const status = String(res.status ?? "unknown");
    const evidence = res.evidence ? `\n  Evidence: ${res.evidence}` : "";
    const stdout = res.stdout ? `\n  stdout: ${String(res.stdout).trim()}` : "";
    const stderr = res.stderr ? `\n  stderr: ${String(res.stderr).trim()}` : "";
    return `[Step ${i + 1}] ${action} → ${status}${evidence}${stdout}${stderr}`;
  });
  const fullTrace = traceLines.join("\n\n") || "(No diagnostic steps recorded.)";

  function handleCopyTrace() {
    navigator.clipboard.writeText(fullTrace).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function renderStopReasonBadge() {
    if (isMaxSteps) {
      return <span className="badge badge--warning">MAX STEPS REACHED</span>;
    }
    if (stopReason === "max_steps" || stopReason === "step_limit") {
      return <span className="badge badge--warning">{stopReason.replace(/_/g, " ").toUpperCase()}</span>;
    }
    if (stopReason === "end_turn" || stopReason === "stop") {
      return <span className="badge badge--success">COMPLETED</span>;
    }
    return <span className="badge badge--neutral">{stopReason.replace(/_/g, " ").toUpperCase()}</span>;
  }

  return (
    <div className="results-page">
      {/* Status header */}
      <div className="results-status-header">
        <div className="results-badges">
          <span className="badge badge--neutral">System Diagnostic</span>
          {renderStopReasonBadge()}
          {analysisStatus && analysisStatus !== "success" && (
            <span className="badge badge--error">
              <Icon name="warning" className="icon-14" />
              ANALYSIS UNAVAILABLE
            </span>
          )}
          <span className="badge badge--id" style={{ fontFamily: "var(--font-mono)" }}>
            ID: {investigationId}
          </span>
        </div>
        <h1 className="results-h1">
          {analysisOk && mostLikelyCause
            ? "Investigation complete"
            : isMaxSteps
            ? "Investigation reached step limit"
            : "Investigation complete — review findings"}
        </h1>
        <p className="results-desc">
          {result.steps_completed} diagnostic step{result.steps_completed !== 1 ? "s" : ""} executed on{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--color-primary)" }}>
            {result.project_path}
          </code>
          {result.truncation_notice ? ` — ${result.truncation_notice}` : ""}
        </p>
      </div>

      {/* Primary cause card */}
      <div className="primary-cause-card">
        <div className="primary-cause-header">
          <div className="primary-cause-left">
            <div className="primary-cause-icon" aria-hidden="true">
              <Icon name={analysisOk && mostLikelyCause ? "crisis_alert" : "help_outline"} className="icon-24" />
            </div>
            <div>
              <span className="primary-cause-label">Primary Cause</span>
              <h2 className="primary-cause-title">
                {mostLikelyCause ?? (
                  analysisStatus
                    ? "Analysis unavailable — see technical details below"
                    : "Cause could not be determined from available evidence"
                )}
              </h2>
            </div>
          </div>
          <div className="exit-code-badge">
            {evidenceSufficient === true
              ? "Evidence: Sufficient"
              : evidenceSufficient === false
              ? "Evidence: Insufficient"
              : stopReason.replace(/_/g, " ")}
          </div>
        </div>

        {analysisError && (
          <p className="primary-cause-desc" style={{ color: "var(--color-error)" }}>
            {analysisError}
          </p>
        )}

        {/* Diagnostic scope callout */}
        <div className="scope-callout">
          <Icon name="verified_user" className="icon-20" style={{ color: "var(--color-info)", marginTop: 2, flexShrink: 0 }} />
          <div>
            <div className="scope-callout-title">Diagnostic Scope</div>
            <p className="scope-callout-desc">
              {analysisOk
                ? "The diagnostic engine ran against your project directory. All findings below are based on actual workspace evidence, not speculation."
                : "The analysis step could not complete. Diagnostic steps ran against your project directory, but the Bedrock analysis phase was unavailable."}
            </p>
          </div>
        </div>
      </div>

      {/* Dual column: evidence + recommendations */}
      <div className="results-dual-grid">
        {/* Evidence card */}
        <div className="evidence-card">
          <div className="evidence-card-header">
            <div className="evidence-card-title-row">
              <Icon name="inventory_2" className="icon-20" style={{ color: "var(--color-primary)" }} />
              <h3 className="evidence-card-title">Preserved Findings</h3>
            </div>
            <span className="evidence-card-stage">
              {result.steps_completed} step{result.steps_completed !== 1 ? "s" : ""} completed
            </span>
          </div>
          <p className="evidence-card-desc">
            Diagnostic steps executed and their findings, based on real workspace evidence:
          </p>

          {/* Evidence from analysis */}
          {confirmedObs.length > 0 && (
            <div className="evidence-list" aria-label="Confirmed observations">
              {confirmedObs.map((obs, i) => (
                <div className="evidence-item" key={`obs-${i}`}>
                  <Icon name="check_circle" className="icon-18" style={{ color: "var(--color-success)", marginTop: 2, flexShrink: 0 }} />
                  <div className="evidence-item-right">
                    <div className="evidence-item-header">
                      <span className="evidence-item-name">Confirmed observation</span>
                      <span className="badge badge--success" style={{ padding: "1px 6px" }}>CONFIRMED</span>
                    </div>
                    <p className="evidence-item-meta">{obs}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Timeline steps */}
          {result.history.length > 0 && (
            <div className="evidence-list" style={{ marginTop: confirmedObs.length ? 8 : 0 }} aria-label="Diagnostic timeline steps">
              {result.history.map((step, i) => {
                const res = step.result as Record<string, unknown>;
                const action = String(res.action ?? "unknown");
                const status = String(res.status ?? "unknown");
                const evidence = res.evidence ? String(res.evidence) : null;
                const isError = ["error", "failed", "timeout"].includes(status);
                const isOk = ["installed", "passed", "ok", "success"].includes(status);

                return (
                  <div
                    className={`evidence-item${isError ? " evidence-item--error" : ""}`}
                    key={`step-${i}`}
                  >
                    <Icon
                      name={isOk ? "check_circle" : isError ? "cancel" : "radio_button_checked"}
                      className="icon-18"
                      style={{
                        color: isOk
                          ? "var(--color-success)"
                          : isError
                          ? "var(--color-error)"
                          : "var(--color-info)",
                        marginTop: 2,
                        flexShrink: 0,
                      }}
                    />
                    <div className="evidence-item-right">
                      <div className="evidence-item-header">
                        <span className={`evidence-item-name${isError ? " evidence-item-name--error" : ""}`}>
                          Step {step.step}: {action}
                        </span>
                        <span
                          className={`badge ${isOk ? "badge--success" : isError ? "badge--error" : "badge--info"}`}
                          style={{ padding: "1px 6px" }}
                        >
                          {status.toUpperCase()}
                        </span>
                      </div>
                      {evidence && <p className="evidence-item-meta">{evidence}</p>}
                      {res.module && (
                        <p className="evidence-item-meta">
                          Module: <code className="code-inline">{String(res.module)}</code>
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {result.history.length === 0 && confirmedObs.length === 0 && (
            <div style={{ textAlign: "center", padding: "32px 16px", color: "var(--color-text-muted)" }}>
              <Icon name="search_off" className="icon-24" style={{ display: "block", margin: "0 auto 8px" }} />
              <p style={{ fontSize: 13 }}>No diagnostic steps were recorded.</p>
            </div>
          )}
        </div>

        {/* Recommendations card */}
        <div className="reco-card">
          <div>
            <div className="reco-card-header">
              <Icon name="tune" className="icon-20" style={{ color: "var(--color-primary)" }} />
              <h3 className="reco-card-title">Recommended Actions</h3>
            </div>
            <p className="reco-card-desc" style={{ marginTop: 8 }}>
              {analysisOk && recommendedNextStep
                ? recommendedNextStep
                : "Review the findings and apply the appropriate fix for your project."}
            </p>

            <div className="reco-actions">
              {/* Primary action: Start new investigation */}
              <button
                className="btn-primary-action"
                type="button"
                onClick={onReset}
                aria-label="Start a new investigation"
              >
                <div className="btn-primary-action-left">
                  <Icon name="refresh" className="icon-20" />
                  <span>Start new investigation</span>
                </div>
                <Icon name="arrow_forward" className="icon-18 btn-primary-action-arrow" />
              </button>

              {/* Evidence Graph & Remediation Suite links */}
              {onViewEvidenceGraph && (
                <button
                  className="btn-secondary-action"
                  type="button"
                  onClick={onViewEvidenceGraph}
                  aria-label="Inspect evidence graph"
                >
                  <div className="btn-secondary-action-left">
                    <Icon name="schema" className="icon-20" style={{ color: "var(--color-primary)" }} />
                    <span>Inspect Evidence Graph</span>
                  </div>
                  <Icon name="arrow_forward" className="icon-18" style={{ color: "var(--color-text-muted)" }} />
                </button>
              )}

              {onRemediate && (
                <button
                  className="btn-secondary-action"
                  type="button"
                  onClick={onRemediate}
                  aria-label="Open remediation suite"
                >
                  <div className="btn-secondary-action-left">
                    <Icon name="build_circle" className="icon-20" style={{ color: "var(--color-primary)" }} />
                    <span>Open Remediation Suite</span>
                  </div>
                  <Icon name="arrow_forward" className="icon-18" style={{ color: "var(--color-text-muted)" }} />
                </button>
              )}

              {/* Secondary action: copy findings */}
              <button
                className="btn-secondary-action"
                type="button"
                onClick={() => {
                  const summary = [
                    `Rootcause Investigation Summary`,
                    `Project: ${result.project_path}`,
                    `Error: ${result.reported_error}`,
                    `Steps: ${result.steps_completed}`,
                    `Stop Reason: ${result.stop_reason}`,
                    mostLikelyCause ? `Most Likely Cause: ${mostLikelyCause}` : "",
                    suggestedFix ? `Suggested Fix: ${suggestedFix}` : "",
                  ].filter(Boolean).join("\n");
                  navigator.clipboard.writeText(summary);
                }}
                aria-label="Copy investigation summary to clipboard"
              >
                <div className="btn-secondary-action-left">
                  <Icon name="content_copy" className="icon-20" style={{ color: "var(--color-text-secondary)" }} />
                  <span>Copy summary to clipboard</span>
                </div>
                <Icon name="add" className="icon-18" style={{ color: "var(--color-text-muted)" }} />
              </button>
            </div>
          </div>

          {/* Suggested fix preview if available */}
          {suggestedFix && (
            <div className="ignore-preview" style={{ marginTop: 8 }}>
              <div className="ignore-preview-header">
                <span>Suggested fix</span>
                <button
                  className="copy-directive-btn"
                  type="button"
                  onClick={() => navigator.clipboard.writeText(suggestedFix)}
                  aria-label="Copy suggested fix"
                >
                  Copy
                </button>
              </div>
              <pre className="ignore-preview-pre">{suggestedFix}</pre>
            </div>
          )}

          {altExplanations.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
                Alternative Explanations
              </div>
              <ul style={{ listStyle: "disc", paddingLeft: 16, display: "flex", flexDirection: "column", gap: 4 }}>
                {altExplanations.map((alt, i) => (
                  <li key={i} style={{ fontSize: 13, lineHeight: "18px", color: "var(--color-text-secondary)" }}>{alt}</li>
                ))}
              </ul>
            </div>
          )}

          {remainingUncertainty.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
                Remaining Uncertainty
              </div>
              <ul style={{ listStyle: "disc", paddingLeft: 16, display: "flex", flexDirection: "column", gap: 4 }}>
                {remainingUncertainty.map((u, i) => (
                  <li key={i} style={{ fontSize: 13, lineHeight: "18px", color: "var(--color-text-secondary)" }}>{u}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="reco-card-footer">
            <button
              className="reco-card-link"
              type="button"
              onClick={() => document.getElementById("trace-disclosure-section")?.scrollIntoView({ behavior: "smooth" })}
              aria-label="Scroll to technical trace"
            >
              <span>View diagnostic trace</span>
              <Icon name="south" className="icon-16" />
            </button>
            <span className="reco-card-resume">
              {result.steps_completed} steps run
            </span>
          </div>
        </div>
      </div>

      {/* Technical trace accordion */}
      <div id="trace-disclosure-section" className="trace-accordion">
        <details open>
          <summary className="trace-accordion-summary">
            <div className="trace-accordion-left">
              <Icon
                name="chevron_right"
                className="icon-20 trace-accordion-arrow"
                style={{ color: "var(--color-text-secondary)" }}
              />
              <span className="trace-accordion-title">
                Technical details &amp; diagnostic trace
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="trace-accordion-badge">
                {result.steps_completed} step{result.steps_completed !== 1 ? "s" : ""} • FastAPI backend
              </span>
            </div>
          </summary>
          <div className="trace-accordion-body">
            <div className="trace-toolbar">
              <div className="trace-meta">
                <span className="trace-meta-dot" aria-hidden="true" />
                <span>Stop reason: {stopReason.replace(/_/g, " ")}</span>
                <span>•</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>
                  Project: {result.project_path}
                </span>
              </div>
              <button
                className={`copy-trace-btn${copied ? " copy-trace-btn--copied" : ""}`}
                type="button"
                onClick={handleCopyTrace}
                aria-label="Copy diagnostic trace to clipboard"
              >
                <Icon name={copied ? "check" : "content_copy"} className="icon-14" />
                <span>{copied ? "Copied!" : "Copy Trace"}</span>
              </button>
            </div>
            <div className="trace-terminal">
              <pre ref={traceRef as React.RefObject<HTMLPreElement>}>{fullTrace}</pre>
            </div>
            {analysisError && (
              <div className="trace-block" style={{ background: "var(--color-error-surface)" }}>
                <div className="trace-block-header">
                  <span>Analysis error</span>
                  <span className="trace-block-status--error">Failed</span>
                </div>
                <pre className="trace-pre" style={{ color: "var(--color-error)", whiteSpace: "pre-wrap" }}>{analysisError}</pre>
              </div>
            )}
            <div className="trace-accordion-footer">
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>
                Investigation ID: {investigationId}
              </span>
              <span>
                FastAPI backend • Strands Orchestrator
              </span>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────
function App() {
  const [appState, setAppState] = useState<AppState>(INITIAL_STATE);
  const [projectPath, setProjectPath] = useState("");
  const [errorText, setErrorText] = useState("");
  const [selectedDemoScenario, setSelectedDemoScenario] = useState<DemoScenario | null>(null);
  const [demoScenarios, setDemoScenarios] = useState<DemoScenario[]>([]);
  const [demoScenariosLoading, setDemoScenariosLoading] = useState(true);
  const [demoScenariosError, setDemoScenariosError] = useState<string | null>(null);
  const [maxSteps, setMaxSteps] = useState(3);
  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Health check on mount
  const checkHealth = useCallback(async () => {
    setAppState((s) => ({ ...s, healthStatus: "checking", healthError: null }));
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error(`Health check HTTP ${res.status}`);
      const data: HealthStatus = await res.json();
      setAppState((s) => ({ ...s, healthStatus: "healthy", health: data }));
    } catch (err) {
      setAppState((s) => ({
        ...s,
        healthStatus: "unhealthy",
        healthError: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Fetch demo scenarios on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setDemoScenariosLoading(true);
        setDemoScenariosError(null);
        const res = await fetch(`${API_BASE}/demo-scenarios`);
        if (!res.ok) throw new Error(`Demo scenarios HTTP ${res.status}`);
        const data: ScenarioListResponse = await res.json();
        if (!cancelled) setDemoScenarios(data.scenarios);
      } catch (err) {
        if (!cancelled)
          setDemoScenariosError(
            err instanceof Error ? err.message : String(err),
          );
      } finally {
        if (!cancelled) setDemoScenariosLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  function selectDemoScenario(scenario: DemoScenario | null) {
    setSelectedDemoScenario(scenario);
    setAppState((s) => ({ ...s, submitError: null }));
  }

  // Elapsed time while investigating
  useEffect(() => {
    if (appState.screen === "investigating") {
      elapsedTimer.current = setInterval(() => {
        setAppState((s) => ({ ...s, elapsedSeconds: s.elapsedSeconds + 1 }));
      }, 1000);
    } else {
      if (elapsedTimer.current) {
        clearInterval(elapsedTimer.current);
        elapsedTimer.current = null;
      }
    }
    return () => {
      if (elapsedTimer.current) clearInterval(elapsedTimer.current);
    };
  }, [appState.screen]);

  const runInvestigation = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!projectPath.trim()) {
        setAppState((s) => ({ ...s, submitError: "Please enter a project directory path." }));
        return;
      }
      if (!errorText.trim()) {
        setAppState((s) => ({ ...s, submitError: "Please paste an error message or stack trace." }));
        return;
      }

      setAppState((s) => ({
        ...s,
        screen: "investigating",
        result: null,
        submitError: null,
        elapsedSeconds: 0,
        investigationId: `run_${Math.random().toString(36).slice(2, 10)}`,
      }));

      try {
        const res = await fetch(`${API_BASE}/investigations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_path: projectPath.trim(),
            error: errorText.trim(),
            max_steps: maxSteps || undefined,
          }),
        });

        const data = await res.json();

        if (!res.ok) {
          setAppState((s) => ({
            ...s,
            screen: "idle",
            submitError: data.detail || `Investigation failed: ${res.status}`,
          }));
          return;
        }

        const investigationResult = data as InvestigationResult;
        setAppState((s) => ({
          ...s,
          screen: "results",
          result: investigationResult,
        }));

        // Construct real incident from actual run
        const rawAnalysis = (investigationResult.analysis as any) || {};
        const isSufficient = rawAnalysis.evidence_sufficient === true || Boolean(rawAnalysis.most_likely_cause);
        const isMaxSteps = investigationResult.stop_reason === "maximum_steps_reached";
        const isError = Boolean(rawAnalysis._analysis_error) || investigationResult.stop_reason === "error";

        const status: "CONFIRMED" | "INCONCLUSIVE" | "FAILED" = isError
          ? "FAILED"
          : isMaxSteps && !isSufficient
          ? "INCONCLUSIVE"
          : "CONFIRMED";

        const newId = `inv-${Math.random().toString(36).slice(2, 7)}`;
        const cause = rawAnalysis.most_likely_cause as string | undefined;
        const fix = rawAnalysis.suggested_fix as string | undefined;

        const firstLine = errorText.trim().split("\n")[0] || "Investigation Run";
        const title = cause ? cause.slice(0, 80) : firstLine.slice(0, 80);

        const newIncident: IncidentRecord = {
          id: newId,
          status,
          model: "Strands Decider 2B",
          timeAgo: "Just now",
          timestamp: Date.now(),
          steps: investigationResult.steps_completed || investigationResult.history?.length || 1,
          duration: `${appState.elapsedSeconds || 1}s`,
          env: projectPath.includes(".venv") ? ".venv" : "Host workspace",
          title,
          snippet: firstLine,
          rootCause: cause,
          resolution: fix ? "Fix Available" : undefined,
          failureReason: rawAnalysis._analysis_error || (isMaxSteps ? "Maximum steps reached" : undefined),
          rawResult: investigationResult,
        };

        setIncidents((prev) => {
          const updated = [newIncident, ...prev];
          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
          } catch {}
          return updated;
        });
        setSelectedIncident(newIncident);
      } catch (err) {
        setAppState((s) => ({
          ...s,
          screen: "idle",
          submitError: err instanceof Error ? err.message : String(err),
        }));
      }
    },
    [projectPath, errorText, maxSteps, appState.elapsedSeconds]
  );

  function handleReset() {
    setProjectPath("");
    setErrorText("");
    setSelectedDemoScenario(null);
    setMaxSteps(3);
    setAppState((s) => ({
      ...s,
      screen: "idle",
      result: null,
      submitError: null,
      elapsedSeconds: 0,
    }));
  }

  const [activeTab, setActiveTab] = useState<NavigationTab>("diagnosis");
  const [incidents, setIncidents] = useState<IncidentRecord[]>(loadSavedIncidents);
  const [selectedIncident, setSelectedIncident] = useState<IncidentRecord | null>(() => {
    const list = loadSavedIncidents();
    return list.length > 0 ? list[0] : null;
  });

  function handleClearHistory() {
    if (window.confirm("Are you sure you want to clear your entire investigation history?")) {
      setIncidents([]);
      setSelectedIncident(null);
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {}
    }
  }

  const screen = appState.screen;

  return (
    <div className="app-shell">
      {/* Top nav — always visible */}
      <TopNav
        health={appState.health}
        healthStatus={appState.healthStatus}
        healthError={appState.healthError}
        projectPath={activeTab === "diagnosis" && screen !== "idle" ? projectPath : activeTab !== "diagnosis" ? projectPath || "~/projects/inventory-api" : ""}
      />

      {/* Sidebar — always visible */}
      <Sidebar
        projectPath={projectPath}
        health={appState.health}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      {/* Main content */}
      <div className="main-layout">
        <main className="main-content" id="main-content" tabIndex={-1}>
          {activeTab === "diagnosis" && (
            <>
              {screen === "idle" && (
                <WorkspaceScreen
                  projectPath={projectPath}
                  setProjectPath={setProjectPath}
                  errorText={errorText}
                  setErrorText={setErrorText}
                  maxSteps={maxSteps}
                  setMaxSteps={setMaxSteps}
                  healthStatus={appState.healthStatus}
                  investigating={false}
                  submitError={appState.submitError}
                  onSubmit={runInvestigation}
                  onReset={handleReset}
                  demoScenarios={demoScenarios}
                  selectedDemoScenario={selectedDemoScenario}
                  onSelectDemoScenario={selectDemoScenario}
                  demoScenariosLoading={demoScenariosLoading}
                  demoScenariosError={demoScenariosError}
                />
              )}

              {screen === "investigating" && (
                <InvestigatingScreen
                  projectPath={projectPath}
                  errorText={errorText}
                  elapsedSeconds={appState.elapsedSeconds}
                />
              )}

              {screen === "results" && appState.result && (
                <ResultsScreen
                  result={appState.result}
                  onReset={handleReset}
                  onViewEvidenceGraph={() => setActiveTab("graph")}
                  onRemediate={() => setActiveTab("remediation")}
                />
              )}
            </>
          )}

          {activeTab === "history" && (
            <IncidentHistoryScreen
              incidents={incidents}
              projectPath={projectPath || "~/projects/inventory-api"}
              onNewInvestigation={() => {
                setActiveTab("diagnosis");
                handleReset();
              }}
              onViewEvidenceGraph={(inc) => {
                setSelectedIncident(inc);
                setActiveTab("graph");
              }}
              onRemediate={(inc) => {
                setSelectedIncident(inc);
                setActiveTab("remediation");
              }}
              onClearHistory={handleClearHistory}
            />
          )}

          {activeTab === "graph" && (
            <EvidenceGraphScreen
              incident={selectedIncident}
              onBackToIncidents={() => setActiveTab("history")}
              onNewInvestigation={() => {
                setActiveTab("diagnosis");
                handleReset();
              }}
              onRemediate={(inc) => {
                setSelectedIncident(inc);
                setActiveTab("remediation");
              }}
            />
          )}

          {activeTab === "remediation" && (
            <RemediationSuiteScreen
              incident={selectedIncident}
              onBackToIncidents={() => setActiveTab("history")}
              onNewInvestigation={() => {
                setActiveTab("diagnosis");
                handleReset();
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
