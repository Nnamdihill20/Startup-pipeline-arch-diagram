import { useState } from "react";

const LAYERS = [
  {
    id: "sources",
    label: "DATA SOURCES",
    color: "#00ff9d",
    nodes: [
      { id: "syslog", label: "Syslog UDP/TCP", lang: "Python", desc: "RFC 3164/5424 listener. Asyncio datagram endpoint — zero-copy reads, no threads." },
      { id: "cloudtrail", label: "AWS CloudTrail", lang: "Python", desc: "S3 poller with watermark tracking. Gzip decompression, paginated list_objects_v2." },
      { id: "webhook", label: "Webhook / HTTP", lang: "Python", desc: "FastAPI receiver for EDR, SaaS, and third-party security tools pushing events." },
      { id: "goagent", label: "Go Collector Agent", lang: "Go", desc: "Deployed on customer infra. Goroutines + channels for high-throughput local collection, gRPC egress." },
    ],
  },
  {
    id: "ingest",
    label: "INGESTION LAYER",
    color: "#00cfff",
    nodes: [
      { id: "queue", label: "Async Event Queue", lang: "Python", desc: "asyncio.Queue (maxsize=10k). Backpressure-aware. Buffers bursts between sources and consumers." },
      { id: "parser", label: "Rust Log Parser", lang: "Rust", desc: "Parses CEF, LEEF, JSON, syslog at wire rate. Memory-safe handling of untrusted input. Emits structured records." },
    ],
  },
  {
    id: "validation",
    label: "SCHEMA & VALIDATION",
    color: "#ff9d00",
    nodes: [
      { id: "normalizer", label: "Normalizer", lang: "Python", desc: "Maps parsed fields to NormalizedEvent schema (ECS-inspired). Pydantic validation, timestamp normalization." },
      { id: "registry", label: "Schema Registry", lang: "Python", desc: "Per-source field requirements. Quarantines malformed events. Tracks field coverage over time." },
    ],
  },
  {
    id: "sink",
    label: "SINK & OBSERVABILITY",
    color: "#ff4d8f",
    nodes: [
      { id: "filesink", label: "File Sink (NDJSON)", lang: "Python", desc: "MVP sink: batched writes to newline-delimited JSON. Rotate to S3 or Kafka when volume justifies it." },
      { id: "monitor", label: "Pipeline Monitor", lang: "Python", desc: "Tracks throughput per source. Fires alerts on data gaps (default: 5min silence = ALERT). Prometheus-ready." },
    ],
  },
];

const LANG_COLORS = {
  Python: { bg: "#1a2a1a", border: "#00ff9d", text: "#00ff9d" },
  Go:     { bg: "#1a1f2a", border: "#00cfff", text: "#00cfff" },
  Rust:   { bg: "#2a1a1a", border: "#ff6b35", text: "#ff6b35" },
};

export default function ArchDiagram() {
  const [active, setActive] = useState(null);
  const [hoveredLayer, setHoveredLayer] = useState(null);

  const activeNode = LAYERS.flatMap(l => l.nodes).find(n => n.id === active);

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080c10",
      fontFamily: "'Courier New', monospace",
      color: "#c8d6e5",
      padding: "40px 32px",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Grid background */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0,
        backgroundImage: `
          linear-gradient(rgba(0,255,157,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,255,157,0.03) 1px, transparent 1px)
        `,
        backgroundSize: "40px 40px",
        pointerEvents: "none",
      }} />

      {/* Scanline */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0,
        background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)",
        pointerEvents: "none",
      }} />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 900, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ marginBottom: 48 }}>
          <div style={{ fontSize: 11, letterSpacing: 6, color: "#00ff9d", marginBottom: 8, opacity: 0.7 }}>
            STEALTH CYBERSEC STARTUP · DATA INFRASTRUCTURE · MVP v0.1
          </div>
          <h1 style={{
            fontSize: "clamp(22px, 4vw, 36px)",
            fontWeight: 700,
            margin: 0,
            letterSpacing: 2,
            color: "#fff",
            textShadow: "0 0 30px rgba(0,255,157,0.3)",
          }}>
            SECURITY EVENT INGESTION PIPELINE
          </h1>
          <div style={{ marginTop: 10, fontSize: 13, color: "#5a7a8a", letterSpacing: 1 }}>
            Click any node to inspect its role, tech, and implementation notes
          </div>
        </div>

        {/* Layers */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {LAYERS.map((layer, li) => (
            <div key={layer.id}>
              {/* Layer */}
              <div
                onMouseEnter={() => setHoveredLayer(layer.id)}
                onMouseLeave={() => setHoveredLayer(null)}
                style={{
                  border: `1px solid ${hoveredLayer === layer.id ? layer.color : "rgba(255,255,255,0.06)"}`,
                  borderRadius: 4,
                  padding: "20px 24px",
                  transition: "border-color 0.2s",
                  background: hoveredLayer === layer.id ? `${layer.color}08` : "rgba(255,255,255,0.01)",
                }}
              >
                {/* Layer header */}
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: layer.color,
                    boxShadow: `0 0 10px ${layer.color}`,
                    flexShrink: 0,
                  }} />
                  <div style={{
                    fontSize: 10, letterSpacing: 4, color: layer.color, fontWeight: 700,
                  }}>
                    {layer.label}
                  </div>
                  <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg, ${layer.color}40, transparent)` }} />
                  <div style={{ fontSize: 10, color: "#3a4a5a", letterSpacing: 1 }}>
                    LAYER {li + 1} / {LAYERS.length}
                  </div>
                </div>

                {/* Nodes */}
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: 10,
                }}>
                  {layer.nodes.map(node => {
                    const lc = LANG_COLORS[node.lang];
                    const isActive = active === node.id;
                    return (
                      <button
                        key={node.id}
                        onClick={() => setActive(isActive ? null : node.id)}
                        style={{
                          background: isActive ? `${layer.color}15` : "rgba(255,255,255,0.02)",
                          border: `1px solid ${isActive ? layer.color : "rgba(255,255,255,0.08)"}`,
                          borderRadius: 4,
                          padding: "14px 16px",
                          cursor: "pointer",
                          textAlign: "left",
                          transition: "all 0.15s",
                          boxShadow: isActive ? `0 0 20px ${layer.color}20` : "none",
                          transform: isActive ? "translateY(-1px)" : "none",
                        }}
                      >
                        <div style={{
                          fontSize: 13, fontWeight: 700, color: isActive ? "#fff" : "#b0c4d4",
                          marginBottom: 8, fontFamily: "'Courier New', monospace",
                          letterSpacing: 0.5,
                        }}>
                          {node.label}
                        </div>
                        <div style={{
                          display: "inline-block",
                          fontSize: 9, letterSpacing: 2,
                          color: lc.text, background: lc.bg,
                          border: `1px solid ${lc.border}40`,
                          padding: "2px 8px", borderRadius: 2,
                        }}>
                          {node.lang.toUpperCase()}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Arrow between layers */}
              {li < LAYERS.length - 1 && (
                <div style={{ display: "flex", justifyContent: "center", padding: "6px 0" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                    <div style={{ width: 1, height: 12, background: "linear-gradient(#ffffff20, #ffffff40)" }} />
                    <div style={{
                      width: 0, height: 0,
                      borderLeft: "5px solid transparent",
                      borderRight: "5px solid transparent",
                      borderTop: "6px solid #ffffff40",
                    }} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Detail panel */}
        <div style={{
          marginTop: 32,
          minHeight: 100,
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 4,
          padding: "20px 24px",
          background: "rgba(0,0,0,0.3)",
          transition: "all 0.2s",
        }}>
          {activeNode ? (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#fff", letterSpacing: 1 }}>
                  {activeNode.label}
                </div>
                <div style={{
                  fontSize: 9, letterSpacing: 3,
                  color: LANG_COLORS[activeNode.lang].text,
                  border: `1px solid ${LANG_COLORS[activeNode.lang].border}50`,
                  padding: "2px 10px", borderRadius: 2,
                  background: LANG_COLORS[activeNode.lang].bg,
                }}>
                  {activeNode.lang.toUpperCase()}
                </div>
              </div>
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7, color: "#8aa0b0", maxWidth: 680 }}>
                {activeNode.desc}
              </p>
            </>
          ) : (
            <div style={{ color: "#2a3a4a", fontSize: 12, letterSpacing: 2, paddingTop: 8 }}>
              ▸ SELECT A NODE TO INSPECT
            </div>
          )}
        </div>

        {/* Legend */}
        <div style={{ marginTop: 24, display: "flex", gap: 24, flexWrap: "wrap" }}>
          {Object.entries(LANG_COLORS).map(([lang, lc]) => (
            <div key={lang} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 10, height: 10, borderRadius: 2,
                background: lc.border, opacity: 0.8,
              }} />
              <span style={{ fontSize: 11, color: "#4a6070", letterSpacing: 2 }}>
                {lang.toUpperCase()}
              </span>
            </div>
          ))}
          <div style={{ marginLeft: "auto", fontSize: 10, color: "#2a3a4a", letterSpacing: 1 }}>
            PYTHON · GO · RUST · MVP STACK
          </div>
        </div>
      </div>
    </div>
  );
}
