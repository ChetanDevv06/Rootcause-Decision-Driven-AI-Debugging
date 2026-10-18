import { useState, useMemo } from "react";
import type { IncidentRecord } from "./IncidentHistory";

function Icon({ name, className = "", style }: { name: string; className?: string; style?: React.CSSProperties }) {
  return (
    <span className={`material-symbols-outlined ${className}`} style={style} aria-hidden="true">
      {name}
    </span>
  );
}

interface EvidenceGraphProps {
  incident: IncidentRecord | null;
  onBackToIncidents: () => void;
  onNewInvestigation: () => void;
  onRemediate: (incident: IncidentRecord) => void;
}

export function EvidenceGraphScreen({
  incident,
  onBackToIncidents,
  onNewInvestigation,
  onRemediate,
}: EvidenceGraphProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string>("root-cause");
  const [layoutMode, setLayoutMode] = useState<"tree" | "mesh" | "timeline">("tree");
  const [zoomScale, setZoomScale] = useState(1.0);
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  // If there's no incident run yet, show a clean, branded Standby state
  if (!incident) {
    return (
      <div className="graph-page">
        <div className="graph-header-card">
          <div className="graph-header-left">
            <div className="graph-breadcrumbs">
              <button type="button" className="breadcrumb-link" onClick={onBackToIncidents}>
                incidents
              </button>
              <span className="text-muted">/</span>
              <span className="text-teal font-medium">evidence-graph</span>
            </div>
            <div className="graph-title-row">
              <Icon name="account_tree" className="icon-24 text-teal" />
              <h1 className="graph-title">Evidence Graph Visualizer</h1>
            </div>
          </div>
        </div>

        <div className="history-empty" style={{ padding: "100px 24px", minHeight: 500, justifyContent: "center" }}>
          <div className="empty-icon-wrap" style={{ width: 64, height: 64, marginBottom: 16 }}>
            <Icon name="schema" className="icon-32 text-muted" />
          </div>
          <h2 style={{ fontSize: 20, color: "var(--color-text-primary)", margin: "0 0 10px 0" }}>
            No active investigation graph
          </h2>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 460, margin: "0 auto 20px auto", fontSize: 13, lineHeight: "22px" }}>
            Run an investigation in Active Diagnosis to generate a deterministic DAG of evidence nodes, symbol traces, and decider verification hypotheses.
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

  // Construct real nodes from the actual investigation history
  const historySteps = incident.rawResult?.history || [];
  const rawAnalysis = incident.rawResult?.analysis || {};

  const nodes = useMemo(() => {
    const list: Array<{
      id: string;
      name: string;
      badge: string;
      badgeType: "primary" | "success" | "warning" | "error" | "info";
      criterion: string;
      obsType: string;
      check: string;
      snippet: string;
      x: number;
      y: number;
    }> = [];

    // Node 1: Initial Error Symptom
    list.push({
      id: "node-symptom",
      name: "Node #1: Reported Error",
      badge: incident.status === "FAILED" ? "Exit Error" : "Traceback",
      badgeType: "error",
      criterion: "Error message or stack trace provided to start investigation.",
      obsType: "Error Ingestion",
      check: "ENTRYPOINT_FAILURE",
      snippet: incident.snippet || incident.rawResult?.reported_error || "No error text recorded",
      x: 60,
      y: 60,
    });

    // Node 2..k: Steps from actual history
    if (historySteps.length > 0) {
      historySteps.forEach((step: any, idx: number) => {
        const stepNum = step.step || idx + 1;
        const res = step.result || {};
        const action = res.action || `Diagnostic Step ${stepNum}`;
        const status = res.status || "completed";
        const evidence = res.evidence || res.stdout || res.stderr || JSON.stringify(res, null, 2);

        list.push({
          id: `step-${stepNum}`,
          name: `Step #${stepNum}: ${action}`,
          badge: status === "success" || status === "ok" ? "Verified" : status,
          badgeType: status === "success" || status === "ok" ? "success" : "info",
          criterion: `Decider executed ${action} against target workspace.`,
          obsType: "Agentic Tool Execution",
          check: `STEP_${stepNum}_${String(status).toUpperCase()}`,
          snippet: typeof evidence === "string" ? evidence : JSON.stringify(evidence, null, 2),
          x: 280 + (idx % 2 === 0 ? 0 : 200),
          y: 180 + idx * 140,
        });
      });
    }

    // Final Node: Synthesized Root Cause
    list.push({
      id: "root-cause",
      name: "Primary Root Cause",
      badge: incident.status === "CONFIRMED" ? "Confirmed Cause" : incident.status,
      badgeType: incident.status === "CONFIRMED" ? "primary" : "warning",
      criterion: rawAnalysis?.most_likely_cause || incident.rootCause || "Evaluation completed.",
      obsType: "Decider 2B Synthesis",
      check: incident.status === "CONFIRMED" ? "DETERMINISTIC_SYNTHESIS" : "INSUFFICIENT_EVIDENCE",
      snippet: rawAnalysis?.suggested_fix || incident.resolution || (incident.rootCause ? `Cause: ${incident.rootCause}` : "No specific cause found"),
      x: 260,
      y: Math.max(480, 220 + historySteps.length * 120),
    });

    return list;
  }, [incident, historySteps, rawAnalysis]);

  const activeNode = nodes.find((n) => n.id === selectedNodeId) || nodes[nodes.length - 1];

  function handleCopySnippet() {
    navigator.clipboard.writeText(activeNode.snippet);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  }

  function handleZoomIn() {
    setZoomScale((prev) => Math.min(prev + 0.15, 1.6));
  }

  function handleZoomOut() {
    setZoomScale((prev) => Math.max(prev - 0.15, 0.7));
  }

  function handleResetZoom() {
    setZoomScale(1.0);
  }

  return (
    <div className="graph-page">
      {/* Top Action & Context Bar */}
      <div className="graph-header-card">
        <div className="graph-header-left">
          <div className="graph-breadcrumbs">
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
            <span className="text-teal font-medium">evidence-graph</span>
            <span className="breadcrumb-dot" />
            <span className="provenance-tag">
              <span className="dot-pulse-teal" />
              Real Run: {incident.id}
            </span>
          </div>

          <div className="graph-title-row">
            <Icon name="account_tree" className="icon-24 text-teal" />
            <h1 className="graph-title">{incident.title}</h1>
            <span className={`badge-resolved ${incident.status === "CONFIRMED" ? "" : "badge-warning"}`}>
              {incident.status === "CONFIRMED" ? "RESOLVED ROOT CAUSE" : incident.status}
            </span>
          </div>
        </div>

        {/* Integrity Badge & Decider Signature */}
        <div className="graph-header-right">
          <div className="provenance-gate-badge">
            <Icon name="verified_user" className="icon-16 text-success" />
            <span>Provenance Gate:</span>
            <span className="font-mono text-success font-semibold">STRICT_DETERMINISTIC</span>
          </div>
          <div className="decider-sig-badge">
            <Icon name="memory" className="icon-16 text-teal" />
            <span>Decider:</span>
            <span className="font-mono text-teal">v2.4.1 (Amazon Bedrock)</span>
          </div>
        </div>
      </div>

      {/* Graph Controls Toolbar */}
      <div className="graph-toolbar">
        {/* Layout Modes */}
        <div className="toolbar-group">
          <button
            type="button"
            className={`toolbar-btn ${layoutMode === "tree" ? "toolbar-btn--active" : ""}`}
            onClick={() => setLayoutMode("tree")}
          >
            <Icon name="schema" className="icon-16" />
            <span>Hierarchical Tree</span>
          </button>
          <button
            type="button"
            className={`toolbar-btn ${layoutMode === "mesh" ? "toolbar-btn--active" : ""}`}
            onClick={() => setLayoutMode("mesh")}
          >
            <Icon name="hub" className="icon-16" />
            <span>Evidence Mesh</span>
          </button>
          <button
            type="button"
            className={`toolbar-btn ${layoutMode === "timeline" ? "toolbar-btn--active" : ""}`}
            onClick={() => setLayoutMode("timeline")}
          >
            <Icon name="timeline" className="icon-16" />
            <span>Timeline Flow</span>
          </button>
        </div>

        {/* Graph Legend */}
        <div className="toolbar-legend">
          <span className="legend-chip legend-chip--success">
            <span className="dot-mini bg-success" />
            Steps Executed ({historySteps.length})
          </span>
          <span className="legend-chip legend-chip--primary">
            <span className="dot-mini bg-primary" />
            Root Cause Node
          </span>
        </div>

        {/* Zoom Controls */}
        <div className="toolbar-zoom">
          <button
            type="button"
            className="zoom-btn"
            onClick={handleZoomIn}
            title="Zoom in"
          >
            <Icon name="add" className="icon-18" />
          </button>
          <button
            type="button"
            className="zoom-btn"
            onClick={handleZoomOut}
            title="Zoom out"
          >
            <Icon name="remove" className="icon-18" />
          </button>
          <button
            type="button"
            className="zoom-reset-btn"
            onClick={handleResetZoom}
            title="Reset scale"
          >
            {Math.round(zoomScale * 100)}%
          </button>
          <button
            type="button"
            className="center-root-btn"
            onClick={() => {
              setSelectedNodeId("root-cause");
              setZoomScale(1.0);
            }}
          >
            <Icon name="filter_center_focus" className="icon-16" />
            <span>Center Root Cause</span>
          </button>
        </div>
      </div>

      {/* Main Split: Node Canvas (Left) + Detailed Inspector (Right) */}
      <div className="graph-workspace-grid">
        {/* Canvas */}
        <div className="graph-canvas-container">
          <div className="canvas-grid-pattern" aria-hidden="true" />
          <div className="canvas-glow canvas-glow--left" aria-hidden="true" />
          <div className="canvas-glow canvas-glow--right" aria-hidden="true" />

          {/* Canvas Floating Metadata Bar */}
          <div className="canvas-meta-bar">
            <div className="canvas-meta-pill">
              <Icon name="grain" className="icon-14 text-teal" />
              <span>Deterministic Graph Visualizer</span>
              <span className="text-muted">·</span>
              <span>Scale: <strong className="text-primary font-mono">{zoomScale.toFixed(2)}x</strong></span>
            </div>
            <div className="canvas-meta-pill">
              <span className="dot-pulse-teal" />
              <span>Verified from Run {incident.id}</span>
            </div>
          </div>

          {/* Scalable Node Stage */}
          <div
            className="canvas-stage"
            style={{
              transform: `scale(${zoomScale})`,
              transformOrigin: "center center",
              transition: "transform 0.25s ease-out",
              height: Math.max(650, 260 + historySteps.length * 140),
            }}
          >
            {/* SVG Connection Lines */}
            <svg className="graph-svg-layer" viewBox="0 0 980 750">
              <defs>
                <marker
                  id="arrow-teal"
                  markerHeight="6"
                  markerWidth="6"
                  orient="auto-start-reverse"
                  refX="8"
                  refY="5"
                  viewBox="0 0 10 10"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#2dd4bf" />
                </marker>
                <marker
                  id="arrow-muted"
                  markerHeight="6"
                  markerWidth="6"
                  orient="auto-start-reverse"
                  refX="8"
                  refY="5"
                  viewBox="0 0 10 10"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748B" />
                </marker>
              </defs>

              {/* Draw connected lines between consecutive nodes */}
              {nodes.map((node, i) => {
                if (i === 0) return null;
                const prev = nodes[i - 1];
                return (
                  <path
                    key={`edge-${i}`}
                    d={`M ${prev.x + 140} ${prev.y + 60} C ${prev.x + 140} ${prev.y + 110}, ${node.x + 140} ${node.y - 40}, ${node.x + 140} ${node.y}`}
                    fill="none"
                    markerEnd="url(#arrow-teal)"
                    stroke="var(--color-primary-container)"
                    strokeWidth="2"
                    strokeDasharray={i === nodes.length - 1 ? undefined : "4,4"}
                  />
                );
              })}
            </svg>

            {/* Dynamic Nodes from real data */}
            {nodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const isRootCause = node.id === "root-cause";

              return (
                <div
                  key={node.id}
                  className={`graph-node ${isRootCause ? "graph-node--primary" : ""} ${isSelected ? "graph-node--selected" : ""}`}
                  style={{
                    left: node.x,
                    top: node.y,
                    width: isRootCause ? 380 : 280,
                  }}
                  onClick={() => setSelectedNodeId(node.id)}
                >
                  <div className="node-header">
                    <span className={`font-semibold flex items-center gap-1 ${isRootCause ? "text-teal" : "text-primary"}`}>
                      <Icon name={isRootCause ? "verified" : "code"} className="icon-16" />
                      {node.name}
                    </span>
                    <span className={`pill-${node.badgeType}-mini font-mono`}>{node.badge}</span>
                  </div>

                  <div className="node-snippet font-mono text-secondary">
                    {node.snippet.slice(0, 140)}
                    {node.snippet.length > 140 ? "..." : ""}
                  </div>

                  <div className="node-footer">
                    <span className="font-mono text-muted text-xs">{node.check}</span>
                    <span className="text-teal font-medium text-xs">
                      {isSelected ? "Inspecting" : "Click to Inspect"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Canvas Mini-map Preview */}
          <div className="canvas-minimap">
            <div className="minimap-header">
              <span>Graph Radar</span>
              <span className="text-teal font-mono">{nodes.length} nodes</span>
            </div>
            <div className="minimap-viewport">
              {nodes.map((n, i) => (
                <div
                  key={n.id}
                  className={`minimap-dot ${n.id === selectedNodeId ? "minimap-dot--focus" : ""}`}
                  style={{
                    left: `${10 + (i * 22) % 110}px`,
                    top: `${8 + Math.floor(i / 5) * 16}px`,
                    background: n.id === "root-cause" ? "var(--color-primary)" : "var(--color-info)",
                  }}
                />
              ))}
              <div className="minimap-frame" />
            </div>
          </div>
        </div>

        {/* Right-Hand Inspection Drawer */}
        <div className="graph-inspector-panel">
          <div className="inspector-content">
            {/* Inspector Header */}
            <div className="inspector-header">
              <div className="inspector-header-left">
                <Icon name="policy" className="icon-22 text-teal" />
                <div>
                  <div className="inspector-overline">Node Inspector</div>
                  <div className="inspector-title">{activeNode.name}</div>
                </div>
              </div>
              <span className={`inspector-status-badge badge-${activeNode.badgeType}`}>
                {activeNode.badge}
              </span>
            </div>

            {/* Decider Policy Criterion */}
            <div className="inspector-card">
              <div className="inspector-card-title text-teal">
                <Icon name="verified" className="icon-16" />
                <span>Decider Assessment</span>
              </div>
              <p className="inspector-card-text">{activeNode.criterion}</p>
            </div>

            {/* Metadata Spec Grid */}
            <div className="inspector-spec-grid">
              <div className="spec-tile">
                <div className="spec-label">Observation Type</div>
                <div className="spec-value">{activeNode.obsType}</div>
              </div>
              <div className="spec-tile">
                <div className="spec-label">Check Code</div>
                <div className="spec-value font-mono text-success">{activeNode.check}</div>
              </div>
              <div className="spec-tile">
                <div className="spec-label">Investigation ID</div>
                <div className="spec-value font-mono text-secondary truncate">{incident.id}</div>
              </div>
              <div className="spec-tile">
                <div className="spec-label">Target Env</div>
                <div className="spec-value font-mono">{incident.env}</div>
              </div>
            </div>

            {/* Telemetry & Raw Artifact View */}
            <div className="inspector-artifact-section">
              <div className="artifact-header">
                <span className="artifact-overline">Diagnostic Output / Trace</span>
                <button
                  type="button"
                  className="btn-copy-artifact"
                  onClick={handleCopySnippet}
                >
                  <Icon name={copiedSnippet ? "check" : "content_copy"} className="icon-14" />
                  <span>{copiedSnippet ? "Copied!" : "Copy Snippet"}</span>
                </button>
              </div>

              <div className="artifact-code-block font-mono">
                <pre>{activeNode.snippet}</pre>
              </div>
            </div>
          </div>

          {/* Action Drawer Footer */}
          <div className="inspector-footer">
            <button
              type="button"
              className="btn-apply-remediation"
              onClick={() => onRemediate(incident)}
            >
              <Icon name="build_circle" className="icon-18" />
              <span>Open in Remediation Suite</span>
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Summary Bar */}
      <div className="graph-bottom-summary">
        <div className="summary-left">
          <span className="flex items-center gap-1 text-primary font-medium">
            <span className="dot-mini bg-success" />
            {nodes.length} nodes synthesized from real run
          </span>
          <span className="text-muted">|</span>
          <span className="text-secondary font-mono">Run: {incident.id}</span>
        </div>

        <div className="summary-right">
          <span className="text-muted">Status:</span>
          <span className="text-teal font-mono font-semibold">{incident.status}</span>
        </div>
      </div>
    </div>
  );
}
