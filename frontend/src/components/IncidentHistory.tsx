import { useState, useMemo } from "react";

function Icon({ name, className = "", style }: { name: string; className?: string; style?: React.CSSProperties }) {
  return (
    <span className={`material-symbols-outlined ${className}`} style={style} aria-hidden="true">
      {name}
    </span>
  );
}

export interface IncidentRecord {
  id: string;
  status: "CONFIRMED" | "INCONCLUSIVE" | "FAILED";
  model: string;
  timeAgo: string;
  timestamp: number;
  steps: number;
  duration: string;
  env: string;
  title: string;
  snippet: string;
  rootCause?: string;
  resolution?: string;
  failureReason?: string;
  actionRequired?: string;
  rawResult?: any;
}

interface IncidentHistoryProps {
  incidents: IncidentRecord[];
  onNewInvestigation: () => void;
  onViewEvidenceGraph: (incident: IncidentRecord) => void;
  onRemediate: (incident: IncidentRecord) => void;
  onClearHistory?: () => void;
  projectPath?: string;
}

export function IncidentHistoryScreen({
  incidents,
  onNewInvestigation,
  onViewEvidenceGraph,
  onRemediate,
  onClearHistory,
  projectPath = "~/projects/inventory-api",
}: IncidentHistoryProps) {
  const [search, setSearch] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState<"ALL" | "CONFIRMED" | "INCONCLUSIVE" | "FAILED">("ALL");
  const [envFilter, setEnvFilter] = useState("all");
  const [exportOpen, setExportOpen] = useState(false);
  const [copiedNotification, setCopiedNotification] = useState<string | null>(null);

  // Compute live metrics strictly from actual recorded user runs
  const totalRuns = incidents.length;
  const confirmedCount = incidents.filter((i) => i.status === "CONFIRMED").length;
  const inconclusiveCount = incidents.filter((i) => i.status === "INCONCLUSIVE").length;
  const failedCount = incidents.filter((i) => i.status === "FAILED").length;
  const confirmedPct = totalRuns > 0 ? ((confirmedCount / totalRuns) * 100).toFixed(1) + "%" : "0%";

  const meanDuration = useMemo(() => {
    if (totalRuns === 0) return "0.00";
    const sum = incidents.reduce((acc, curr) => {
      const match = curr.duration.match(/[\d.]+/);
      return acc + (match ? parseFloat(match[0]) : 1.5);
    }, 0);
    return (sum / totalRuns).toFixed(2);
  }, [incidents, totalRuns]);

  // Unique environments in real data
  const availableEnvs = useMemo(() => {
    const set = new Set<string>();
    incidents.forEach((i) => {
      if (i.env) set.add(i.env);
    });
    return Array.from(set);
  }, [incidents]);

  const filteredIncidents = useMemo(() => {
    return incidents.filter((item) => {
      if (outcomeFilter !== "ALL" && item.status !== outcomeFilter) return false;
      if (envFilter !== "all" && item.env !== envFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const match =
          item.id.toLowerCase().includes(q) ||
          item.title.toLowerCase().includes(q) ||
          item.snippet.toLowerCase().includes(q) ||
          item.env.toLowerCase().includes(q);
        if (!match) return false;
      }
      return true;
    });
  }, [incidents, search, outcomeFilter, envFilter]);

  function handleExport(format: "json" | "csv" | "ndjson") {
    setExportOpen(false);
    if (incidents.length === 0) {
      setCopiedNotification("No incidents to export");
      setTimeout(() => setCopiedNotification(null), 2500);
      return;
    }

    let content = "";
    let mime = "text/plain";
    let filename = `rootcause-audit-log.${format}`;

    if (format === "json") {
      content = JSON.stringify(incidents, null, 2);
      mime = "application/json";
    } else if (format === "csv") {
      const headers = "id,status,title,env,steps,duration,timeAgo\n";
      const rows = incidents
        .map(
          (i) =>
            `"${i.id}","${i.status}","${i.title.replace(/"/g, '""')}","${i.env}",${i.steps},"${i.duration}","${i.timeAgo}"`
        )
        .join("\n");
      content = headers + rows;
      mime = "text/csv";
    } else {
      content = incidents.map((i) => JSON.stringify(i)).join("\n");
      mime = "application/x-ndjson";
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setCopiedNotification(`Exported ${incidents.length} run(s) as ${format.toUpperCase()}`);
    setTimeout(() => setCopiedNotification(null), 2500);
  }

  return (
    <div className="incident-history-page">
      {/* Toast Notification */}
      {copiedNotification && (
        <div className="history-toast">
          <Icon name="check_circle" className="icon-18 text-success" />
          <span>{copiedNotification}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="history-header">
        <div className="history-header-left">
          <div className="history-breadcrumbs">
            <span className="text-secondary">Workspace:</span>
            <span className="text-primary font-mono">{projectPath}</span>
            <span className="text-muted">/</span>
            <span className="text-secondary">branch:</span>
            <span className="text-teal font-mono">main</span>
            <span className="breadcrumb-dot" />
            <span className="history-audit-tag">Audit Log</span>
          </div>

          <div className="history-title-row">
            <h1 className="history-title">Incident History</h1>
            <span className="history-stream-badge">
              <span className="dot-pulse-teal" />
              {totalRuns > 0 ? `${totalRuns} Real Run(s) Recorded` : "Audit Stream Standby"}
            </span>
          </div>

          <p className="history-subtitle">
            Deterministic run log of simulated execution trees, test regressions, and agent-verified root cause diagnoses executed in this session.
          </p>
        </div>

        {/* Action Panel */}
        <div className="history-actions">
          {totalRuns > 0 && onClearHistory && (
            <button
              type="button"
              className="btn-export"
              onClick={onClearHistory}
              title="Clear all recorded investigation history"
              style={{ color: "var(--color-error)" }}
            >
              <Icon name="delete_sweep" className="icon-16 text-error" />
              <span>Clear History</span>
            </button>
          )}

          <div className="history-export-wrapper">
            <button
              className="btn-export"
              onClick={() => setExportOpen((prev) => !prev)}
              aria-expanded={exportOpen}
              type="button"
              disabled={totalRuns === 0}
            >
              <Icon name="file_download" className="icon-16 text-muted" />
              <span>Export Audit Log</span>
              <Icon name="expand_more" className="icon-16 text-muted" />
            </button>

            {exportOpen && (
              <div className="history-export-menu" role="menu">
                <button
                  type="button"
                  className="history-export-item"
                  onClick={() => handleExport("json")}
                >
                  <Icon name="data_object" className="icon-16 text-teal" />
                  <span>JSON Format (.json)</span>
                </button>
                <button
                  type="button"
                  className="history-export-item"
                  onClick={() => handleExport("csv")}
                >
                  <Icon name="table_view" className="icon-16 text-success" />
                  <span>Comma-Separated (.csv)</span>
                </button>
                <button
                  type="button"
                  className="history-export-item"
                  onClick={() => handleExport("ndjson")}
                >
                  <Icon name="terminal" className="icon-16 text-muted" />
                  <span>CLI Trace Dump (.ndjson)</span>
                </button>
              </div>
            )}
          </div>

          <button
            className="btn-new-investigation"
            onClick={onNewInvestigation}
            type="button"
          >
            <Icon name="play_arrow" className="icon-18" />
            <span>New Investigation</span>
          </button>
        </div>
      </div>

      {/* Summary Metrics Bar (Bento Tonal Cards computed from real history) */}
      <div className="history-metrics-grid">
        {/* Metric 1 */}
        <div className="metric-card">
          <div className="metric-card-top">
            <span className="metric-label">Total Runs</span>
            <Icon name="analytics" className="icon-18 text-muted" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{totalRuns}</span>
            <span className="metric-sub">recorded</span>
          </div>
          <div className="metric-footer text-secondary">
            <span className="w-1-5 h-1-5 rounded-full bg-primary" />
            <span>Actual runs executed</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="metric-card">
          <div className="metric-card-top">
            <span className="metric-label">Confirmed Causes</span>
            <Icon name="verified" className="icon-18 text-success" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value text-success">{confirmedCount}</span>
            <span className="metric-pill-success">{confirmedPct}</span>
          </div>
          <div className="metric-footer text-secondary">
            <span>Diagnosed causes</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="metric-card">
          <div className="metric-card-top">
            <span className="metric-label">Inconclusive</span>
            <Icon name="help_center" className="icon-18 text-warning" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value text-warning">{inconclusiveCount}</span>
            <span className="metric-sub text-muted">runs</span>
          </div>
          <div className="metric-footer text-secondary">
            <span>Awaiting more steps/telemetry</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="metric-card">
          <div className="metric-card-top">
            <span className="metric-label">Failed / Aborts</span>
            <Icon name="dangerous" className="icon-18 text-error" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value text-error">{failedCount}</span>
            <span className="metric-sub text-error">errors</span>
          </div>
          <div className="metric-footer text-secondary">
            <span>Errors or exceptions</span>
          </div>
        </div>

        {/* Metric 5 */}
        <div className="metric-card">
          <div className="metric-card-top">
            <span className="metric-label">Mean Diagnosis Time</span>
            <Icon name="speed" className="icon-18 text-teal" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{meanDuration}</span>
            <span className="metric-sub text-teal">sec</span>
          </div>
          <div className="metric-footer metric-footer--sparkline">
            <span className="text-secondary">Average duration</span>
            <svg className="sparkline-svg" fill="none" viewBox="0 0 64 16">
              <path
                d="M1 12L12 10L24 13L36 7L48 9L63 3"
                stroke="var(--color-primary)"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.5"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Filter & Query Control Center */}
      <div className="history-filter-bar">
        {/* Search */}
        <div className="history-search-wrapper">
          <Icon name="search" className="history-search-icon" />
          <input
            className="history-search-input"
            type="text"
            placeholder="Filter by incident ID, stack symbol, or message..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="history-search-kbd">
            <kbd>⌘K</kbd>
          </div>
        </div>

        {/* Filters */}
        <div className="history-filter-controls">
          <div className="history-outcome-pills">
            <button
              type="button"
              className={`pill-btn ${outcomeFilter === "ALL" ? "pill-btn--active" : ""}`}
              onClick={() => setOutcomeFilter("ALL")}
            >
              All ({totalRuns})
            </button>
            <button
              type="button"
              className={`pill-btn ${outcomeFilter === "CONFIRMED" ? "pill-btn--active" : ""}`}
              onClick={() => setOutcomeFilter("CONFIRMED")}
            >
              Confirmed ({confirmedCount})
            </button>
            <button
              type="button"
              className={`pill-btn ${outcomeFilter === "INCONCLUSIVE" ? "pill-btn--active" : ""}`}
              onClick={() => setOutcomeFilter("INCONCLUSIVE")}
            >
              Inconclusive ({inconclusiveCount})
            </button>
            <button
              type="button"
              className={`pill-btn ${outcomeFilter === "FAILED" ? "pill-btn--active" : ""}`}
              onClick={() => setOutcomeFilter("FAILED")}
            >
              Failed ({failedCount})
            </button>
          </div>

          <div className="filter-divider" />

          {/* Environment dropdown */}
          <div className="history-select-wrapper">
            <select
              className="history-select"
              value={envFilter}
              onChange={(e) => setEnvFilter(e.target.value)}
            >
              <option value="all">Environment: All</option>
              {availableEnvs.map((env) => (
                <option key={env} value={env}>
                  {env}
                </option>
              ))}
            </select>
            <Icon name="expand_more" className="select-arrow-icon" />
          </div>

          {/* Sort */}
          <button type="button" className="history-sort-btn">
            <Icon name="swap_vert" className="icon-16" />
            <span>Newest First</span>
          </button>
        </div>
      </div>

      {/* Incident List */}
      <div className="history-list">
        {totalRuns === 0 ? (
          <div className="history-empty" style={{ padding: "70px 20px" }}>
            <div className="empty-icon-wrap" style={{ width: 56, height: 56 }}>
              <Icon name="history" className="icon-28 text-muted" />
            </div>
            <h3 style={{ fontSize: 18, color: "var(--color-text-primary)", margin: "0 0 8px 0" }}>
              No investigation runs recorded yet
            </h3>
            <p style={{ color: "var(--color-text-secondary)", maxWidth: 440, margin: "0 auto 16px auto", fontSize: 13, lineHeight: "20px" }}>
              All actual investigations executed in Active Diagnosis will be logged here with their deterministic evidence DAGs, steps, and resolution state.
            </p>
            <button
              type="button"
              className="btn-new-investigation"
              onClick={onNewInvestigation}
            >
              <Icon name="play_arrow" className="icon-18" />
              <span>Start First Investigation</span>
            </button>
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="history-empty">
            <div className="empty-icon-wrap">
              <Icon name="search_off" className="icon-24 text-muted" />
            </div>
            <h3>No matching incidents found</h3>
            <p>No recorded diagnostic logs match your current query or status filters.</p>
            <button
              type="button"
              className="btn-clear-filters"
              onClick={() => {
                setSearch("");
                setOutcomeFilter("ALL");
                setEnvFilter("all");
              }}
            >
              Clear Filters
            </button>
          </div>
        ) : (
          filteredIncidents.map((incident) => {
            const isConfirmed = incident.status === "CONFIRMED";
            const isInconclusive = incident.status === "INCONCLUSIVE";
            const isFailed = incident.status === "FAILED";

            return (
              <div
                key={incident.id}
                className={`incident-card ${
                  isConfirmed
                    ? "incident-card--confirmed"
                    : isInconclusive
                    ? "incident-card--inconclusive"
                    : "incident-card--failed"
                }`}
              >
                {/* Accent border strip */}
                <div
                  className={`incident-card-stripe ${
                    isConfirmed
                      ? "stripe-teal"
                      : isInconclusive
                      ? "stripe-warning"
                      : "stripe-error"
                  }`}
                />

                {/* Top Row: ID, Badges, Time, Telemetry */}
                <div className="incident-card-header">
                  <div className="incident-card-meta-left">
                    <span className="incident-id font-mono">{incident.id}</span>

                    {/* Status Pill */}
                    <span
                      className={`incident-status-pill ${
                        isConfirmed
                          ? "pill-confirmed"
                          : isInconclusive
                          ? "pill-inconclusive"
                          : "pill-failed"
                      }`}
                    >
                      <span className="dot-mini" />
                      {incident.status}
                    </span>

                    {/* Decider */}
                    <span className="incident-decider-badge">
                      <Icon name="memory" className="icon-14 text-teal" />
                      <span>{incident.model}</span>
                    </span>

                    {/* Time */}
                    <span className="incident-time">
                      <Icon name="timelapse" className="icon-14 text-muted" />
                      <span>{incident.timeAgo}</span>
                    </span>
                  </div>

                  {/* Telemetry right */}
                  <div className="incident-card-telemetry">
                    <span>
                      Steps: <strong>{incident.steps}</strong>
                    </span>
                    <span>
                      Duration:{" "}
                      <strong className={isFailed ? "text-error" : "text-teal"}>
                        {incident.duration}
                      </strong>
                    </span>
                    <span className="env-badge">{incident.env}</span>
                  </div>
                </div>

                {/* Middle Row: Title & Stack Snippet & Buttons */}
                <div className="incident-card-body">
                  <div className="incident-body-main">
                    <div className="incident-title-row">
                      <Icon
                        name={isConfirmed ? "check_circle" : isInconclusive ? "help_center" : "cancel"}
                        className={`icon-18 ${isConfirmed ? "text-success" : isInconclusive ? "text-warning" : "text-error"}`}
                      />
                      <h2 className="incident-title-text">{incident.title}</h2>
                    </div>

                    <div className="incident-snippet font-mono">{incident.snippet}</div>
                  </div>

                  {/* Actions */}
                  <div className="incident-card-actions">
                    <button
                      type="button"
                      className="btn-card-action"
                      onClick={() => onViewEvidenceGraph(incident)}
                      title="Inspect interactive provenance DAG"
                    >
                      <Icon name="schema" className="icon-16 text-teal" />
                      <span>Evidence Graph</span>
                    </button>

                    <button
                      type="button"
                      className="btn-card-action btn-card-action--primary"
                      onClick={() => onRemediate(incident)}
                      title="View remediation options"
                    >
                      <Icon name="build_circle" className="icon-16" />
                      <span>Remediate</span>
                    </button>
                  </div>
                </div>

                {/* Bottom Row: Resolution / Root Cause Footnote */}
                <div className="incident-card-footer">
                  <div className="footer-left">
                    {incident.rootCause && (
                      <>
                        <span className="text-secondary font-medium">Root Cause:</span>
                        <span>{incident.rootCause}</span>
                      </>
                    )}
                    {incident.failureReason && (
                      <>
                        <span className="text-secondary font-medium">Failure Reason:</span>
                        <span className="text-error font-mono">{incident.failureReason}</span>
                      </>
                    )}
                  </div>

                  <div className="footer-right">
                    {incident.resolution && (
                      <div className="resolution-badge">
                        <Icon name="task_alt" className="icon-16 text-success" />
                        <span>{incident.resolution}</span>
                      </div>
                    )}
                    {incident.actionRequired && (
                      <span className="text-muted">{incident.actionRequired}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Footer */}
      {totalRuns > 0 && (
        <div className="history-pagination-footer">
          <div className="pagination-info">
            <span>
              Showing <strong className="font-mono text-primary">1–{filteredIncidents.length}</strong> of{" "}
              <strong className="font-mono text-primary">{totalRuns}</strong> actual run(s)
            </span>
          </div>

          <div className="pagination-controls">
            <button type="button" className="page-btn page-btn-nav" disabled>
              <Icon name="chevron_left" className="icon-16" />
            </button>
            <button type="button" className="page-btn page-btn--active">1</button>
            <button type="button" className="page-btn page-btn-nav" disabled>
              <Icon name="chevron_right" className="icon-16" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
