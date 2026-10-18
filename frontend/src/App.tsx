"use client";

import { useState, useCallback, useEffect } from "react";

const API_BASE = "/api";

interface HealthStatus {
  status: string;
  service: string;
  version: string;
  modules: Record<string, boolean>;
  decider_reachable: boolean;
  bedrock_configured: boolean;
}

interface InvestigationResult {
  project_path: string;
  reported_error: string;
  steps_completed: number;
  actions_executed: string[];
  evidence_history: string[];
  history: Array<Record<string, unknown>>;
  stop_reason: string;
  truncation_notice?: string | null;
  analysis: Record<string, unknown> | null;
  analysis_status?: string | null;
  analysis_error?: string | null;
}

interface AppState {
  status: "idle" | "checking" | "healthy" | "unhealthy";
  health: HealthStatus | null;
  healthError: string | null;
  investigating: boolean;
  result: InvestigationResult | null;
  error: string | null;
}

const INITIAL_STATE: AppState = {
  status: "idle",
  health: null,
  healthError: null,
  investigating: false,
  result: null,
  error: null,
};

function App() {
  const [state, setState] = useState<AppState>(INITIAL_STATE);

  const [projectPath, setProjectPath] = useState("");
  const [errorText, setErrorText] = useState("");
  const [maxSteps, setMaxSteps] = useState(3);

  const checkHealth = useCallback(async () => {
    setState((s) => ({ ...s, status: "checking", healthError: null }));
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
      const data: HealthStatus = await res.json();
      setState((s) => ({ ...s, status: "healthy", health: data }));
    } catch (err) {
      setState((s) => ({
        ...s,
        status: "unhealthy",
        healthError: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  const runInvestigation = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!projectPath.trim()) {
      setState((s) => ({ ...s, error: "Please enter a project directory." }));
      return;
    }
    if (!errorText.trim()) {
      setState((s) => ({ ...s, error: "Please enter an error message or stack trace." }));
      return;
    }

    setState((s) => ({
      ...s,
      investigating: true,
      result: null,
      error: null,
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
        setState((s) => ({
          ...s,
          investigating: false,
          error: data.detail || `Investigation failed: ${res.status}`,
        }));
        return;
      }

      setState((s) => ({
        ...s,
        investigating: false,
        result: data as InvestigationResult,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        investigating: false,
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }, [projectPath, errorText, maxSteps]);

  // Check health on mount
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  return (
    <div className="app">
      <header className="header">
        <div className="logo">RC</div>
        <div className="brand">
          <h1>Rootcause</h1>
          <p>Every failure has a reason. Find it with evidence.</p>
        </div>
        {state.status === "healthy" && (
          <span className="status-bar ok">
            <span className="status-dot"></span>
            API online · Decider {state.health?.decider_reachable ? "reachable" : "unreachable"} · Bedrock{" "}
            {state.health?.bedrock_configured ? "configured" : "not configured"}
          </span>
        )}
        {state.status === "unhealthy" && (
          <span className="status-bar warn">
            <span className="status-dot"></span>
            API unhealthy: {state.healthError}
          </span>
        )}
      </header>

      <div className="card">
        <form onSubmit={runInvestigation} className="form-grid">
          <div className="input-group">
            <label>Project directory</label>
            <input
              type="text"
              placeholder="e.g. ./examples/fixtures/missing_dependency"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              disabled={state.investigating}
            />
          </div>
          <div className="input-group">
            <label>Reported error / stack trace</label>
            <textarea
              placeholder="e.g. ModuleNotFoundError: No module named 'psycopg'"
              value={errorText}
              onChange={(e) => setErrorText(e.target.value)}
              disabled={state.investigating}
            />
          </div>
          <div className="input-group">
            <label>Max steps</label>
            <select
              value={maxSteps}
              onChange={(e) => setMaxSteps(parseInt(e.target.value, 10))}
              disabled={state.investigating}
            >
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
              <option value={4}>4</option>
              <option value={5}>5</option>
            </select>
          </div>
          <button type="submit" className="btn-primary" disabled={state.investigating || state.status !== "healthy"}>
            {state.investigating ? (
              <>
                <span className="spinner" style={{ marginRight: 8 }}></span>
                Running investigation…
              </>
            ) : (
              "Run Investigation"
            )}
          </button>
        </form>

        {state.error && (
          <div className="warning-banner">
            <h4>Error</h4>
            <p>{state.error}</p>
          </div>
        )}

        {state.result && (
          <>
            <div className="results-title">
              Investigation Results
              <span
                style={{
                  marginLeft: "auto",
                  fontSize: "11px",
                  fontWeight: "600",
                  textTransform: "uppercase",
                  color: state.result.stop_reason === "maximum_steps_reached" ? varWarning : varMuted,
                }}
              >
                {state.result.stop_reason.replace("_", " ").toUpperCase()}
              </span>
            </div>

            {state.result.truncation_notice && (
              <div className="warning-banner">
                <h4>Investigation truncated</h4>
                <p>{state.result.truncation_notice}</p>
              </div>
            )}

            {state.result.analysis?._analysis_status && state.result.analysis?._analysis_status !== "success" && (
              <div className="warning-banner">
                <h4>Analysis unavailable</h4>
                <p>
                  {state.result.analysis?._analysis_error ||
                  `Analysis status: ${state.result.analysis._analysis_status}`}
                </p>
              </div>
            )}

            <div className="result-grid">
              <div className="result-card">
                <h3>Most likely cause</h3>
                <p>
                  {state.result.analysis?.most_likely_cause ?? "Analysis unavailable"}
                </p>
              </div>
              <div className="result-card">
                <h3>Evidence sufficient</h3>
                <p className={state.result.analysis?.evidence_sufficient ? "evidence-sufficient" : "evidence-insufficient"}>
                  {state.result.analysis?.evidence_sufficient !== undefined
                    ? String(state.result.analysis.evidence_sufficient)
                    : "N/A"}
                </p>
              </div>
              <div className="result-card" style={{ gridColumn: "span 2" }}>
                <h3>Confirmed observations</h3>
                <ul>
                  {(state.result.analysis?.confirmed_observations as string[] | undefined)?.length ? (
                    (state.result.analysis?.confirmed_observations as string[]).map((o, i) => (
                      <li key={i}>{o}</li>
                    ))
                  ) : (
                    <li style={{ color: "#71717a" }}>None recorded</li>
                  )}
                </ul>
              </div>
              <div className="result-card" style={{ gridColumn: "span 2" }}>
                <h3>Alternative explanations</h3>
                <ul>
                  {(state.result.analysis?.alternative_explanations as string[] | undefined)?.length ? (
                    (state.result.analysis?.alternative_explanations as string[]).map((a, i) => (
                      <li key={i}>{a}</li>
                    ))
                  ) : (
                    <li style={{ color: "#71717a" }}>None recorded</li>
                  )}
                </ul>
              </div>
              <div className="result-card" style={{ gridColumn: "span 2" }}>
                <h3>Recommended next step</h3>
                <p>
                  {state.result.analysis?.recommended_next_step || "None"}
                </p>
              </div>
              <div className="result-card" style={{ gridColumn: "span 2" }}>
                <h3>Suggested fix</h3>
                {state.result.analysis?.suggested_fix ? (
                  <div className="suggested-fix">{state.result.analysis.suggested_fix}</div>
                ) : (
                  <p style={{ color: "#71717a" }}>None</p>
                )}
              </div>
              <div className="result-card" style={{ gridColumn: "span 2" }}>
                <h3>Remaining uncertainty</h3>
                <ul>
                  {(state.result.analysis?.remaining_uncertainty as string[] | undefined)?.length ? (
                    (state.result.analysis?.remaining_uncertainty as string[]).map((u, i) => (
                      <li key={i}>{u}</li>
                    ))
                  ) : (
                    <li style={{ color: "#71717a" }}>None recorded</li>
                  )}
                </ul>
              </div>
            </div>

            <div className="card" style={{ marginTop: 24 }}>
              <div className="results-title">Diagnostic timeline</div>
              <div className="timeline">
                {state.result.history.length === 0 ? (
                  <div className="empty-state">
                    <p>No diagnostic actions were executed.</p>
                  </div>
                ) : (
                  state.result.history.map((step, i) => {
                    const result = step.result as Record<string, unknown>;
                    const action = result.action || "unknown";
                    const status = result.status || "unknown";
                    const statusClass = `status-${String(status).replace(/\s/g, "_")}`;
                    return (
                      <div className="timeline-item" key={i}>
                        <div className="timeline-header">
                          <span className="timeline-action">{action}</span>
                          <span className="timeline-step">Step {step.step}</span>
                          <span className={`timeline-status ${statusClass}`}>{status}</span>
                        </div>
                        {result.module && (
                          <p style={{ fontSize: "12px", color: "#a1a1aa", marginBottom: 8 }}>
                            Module: <code style={{ color: "#c4b5fd" }}>{result.module}</code>{" "}
                            · Interpreter:{" "}
                            <code style={{ color: "#c4b5fd" }}>{result.interpreter}</code>
                          </p>
                        )}
                        {result.evidence && (
                          <p style={{ fontSize: "13px", color: "#fafafa" }}>{result.evidence}</p>
                        )}
                        {(result.stdout || result.stderr) && (
                          <pre className="timeline-pre">
                            {(result.stdout || "").trim() || (result.stderr || "").trim()}
                          </pre>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </>
        )}

        {!state.result && !state.error && state.status === "healthy" && (
          <div className="empty-state">
            <p>Ready to investigate. Enter a project path and error above.</p>
          </div>
        )}
      </div>
    </div>
  );
}

const varMuted = "#a1a1aa";
const varWarning = "#f59e0b";

export default App;
