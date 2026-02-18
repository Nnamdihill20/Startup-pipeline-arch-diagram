# 🗺️ sec-pipeline-arch

> Interactive architecture diagram for the security event ingestion pipeline. Built as a React component for internal documentation, onboarding, and stakeholder demos.

Dark terminal aesthetic. Click any node to inspect its role, tech stack rationale, and implementation notes.

---

## Preview

```
╔══════════════════════════════════════════════════════════╗
║  STEALTH CYBERSEC STARTUP · DATA INFRASTRUCTURE · MVP   ║
║                                                         ║
║  SECURITY EVENT INGESTION PIPELINE                      ║
╠══════════════════════════════════════════════════════════╣
║  ● DATA SOURCES ─────────────────────────────────────── ║
║  [ Syslog UDP/TCP ] [ AWS CloudTrail ] [ Webhook/HTTP ] ║
║  [ Go Collector Agent ]                                 ║
║                         ▼                               ║
║  ● INGESTION LAYER ───────────────────────────────────  ║
║  [ Async Event Queue ]  [ Rust Log Parser ]             ║
║                         ▼                               ║
║  ● SCHEMA & VALIDATION ──────────────────────────────   ║
║  [ Normalizer ]  [ Schema Registry ]                    ║
║                         ▼                               ║
║  ● SINK & OBSERVABILITY ──────────────────────────────  ║
║  [ File Sink (NDJSON) ]  [ Pipeline Monitor ]           ║
╚══════════════════════════════════════════════════════════╝
```

---

## What It Is

A single-file React component (`arch_diagram.jsx`) that renders an interactive, layered diagram of the ingestion pipeline. Designed to:

- **Onboard** new engineers quickly — click any node to understand what it does and why
- **Document** tech decisions (Python vs Go vs Rust tradeoffs) inline with the architecture
- **Demo** the stack to stakeholders without a slide deck

No build step. No dependencies beyond React. Drop it into any React environment or Claude artifact runner.

---

## Nodes & Layers

### Layer 1 — Data Sources
| Node | Lang | Description |
|------|------|-------------|
| Syslog UDP/TCP | Python | RFC 3164/5424 asyncio listener |
| AWS CloudTrail | Python | S3 poller with watermark tracking |
| Webhook / HTTP | Python | FastAPI receiver for EDR / SaaS push |
| Go Collector Agent | Go | High-throughput on-prem agent, gRPC egress |

### Layer 2 — Ingestion Layer
| Node | Lang | Description |
|------|------|-------------|
| Async Event Queue | Python | asyncio.Queue with backpressure (maxsize=10k) |
| Rust Log Parser | Rust | CEF/LEEF/JSON/syslog parser at wire rate |

### Layer 3 — Schema & Validation
| Node | Lang | Description |
|------|------|-------------|
| Normalizer | Python | Maps parsed fields → NormalizedEvent (ECS-inspired) |
| Schema Registry | Python | Per-source field requirements, quarantine, coverage tracking |

### Layer 4 — Sink & Observability
| Node | Lang | Description |
|------|------|-------------|
| File Sink (NDJSON) | Python | Batched writes, swap for Kafka/S3 when ready |
| Pipeline Monitor | Python | Gap detection, throughput tracking, Prometheus-ready |

---

## Usage

### As a Claude Artifact

Paste `arch_diagram.jsx` directly into a Claude artifact runner. It uses no external dependencies beyond React and renders immediately.

### In a React App

```bash
# Copy the component into your project
cp arch_diagram.jsx src/components/ArchDiagram.jsx

# Import and render
import ArchDiagram from './components/ArchDiagram';

function App() {
  return <ArchDiagram />;
}
```

No additional packages required. Uses only React hooks (`useState`).

### Standalone (Vite)

```bash
npm create vite@latest arch-viewer -- --template react
cd arch-viewer
cp /path/to/arch_diagram.jsx src/App.jsx
npm install && npm run dev
```

---

## Customization

The diagram is driven entirely by the `LAYERS` array at the top of the file. To add a node, layer, or change colors:

```js
const LAYERS = [
  {
    id: "sources",
    label: "DATA SOURCES",
    color: "#00ff9d",          // Layer accent color
    nodes: [
      {
        id: "my_new_source",
        label: "Kafka Consumer",
        lang: "Go",            // Controls badge color: "Python" | "Go" | "Rust"
        desc: "Reads from internal Kafka topics. Consumer group per pipeline stage.",
      },
    ],
  },
  // ...
];
```

To add a new language badge color, extend `LANG_COLORS`:

```js
const LANG_COLORS = {
  Python: { bg: "#1a2a1a", border: "#00ff9d", text: "#00ff9d" },
  Go:     { bg: "#1a1f2a", border: "#00cfff", text: "#00cfff" },
  Rust:   { bg: "#2a1a1a", border: "#ff6b35", text: "#ff6b35" },
  Java:   { bg: "#2a1f1a", border: "#f89820", text: "#f89820" }, // example
};
```

---

## Design

- **Aesthetic**: Terminal / CRT monitor. Dark background, grid overlay, scanlines, glowing accents.
- **Color system**: Each layer has its own accent color. Lang badges use distinct per-language colors.
- **Interaction**: Click to select/deselect nodes. Detail panel updates inline. Hover highlights the active layer.
- **Font**: `Courier New` monospace throughout — intentional, matches the security tooling context.

---

## File

```
sec-pipeline-arch/
└── arch_diagram.jsx    # Everything. Single file, no build required.
```

---

## Related

- [`sec-pipeline`](../sec-pipeline) — The actual Python ingestion pipeline this diagram documents
- Go collector agent — high-throughput event collection (coming soon)
- Rust log parser — wire-rate CEF/LEEF/syslog parser (coming soon)

---
# 🛡️ sec-pipeline

> High-throughput security event ingestion pipeline — MVP scaffold for cybersecurity data infrastructure.

Built for stealth-stage teams that need to get security data flowing fast, without over-engineering it. Python core, designed to slot Go collectors and a Rust parser in as volume grows.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     DATA SOURCES                        │
│  [ Syslog UDP ]  [ CloudTrail S3 ]  [ Webhook / HTTP ]  │
│              [ Go Collector Agent ]                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  INGESTION LAYER                        │
│         [ asyncio.Queue ]  [ Rust Log Parser ]          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               SCHEMA & VALIDATION                       │
│          [ Normalizer ]  [ Schema Registry ]            │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              SINK & OBSERVABILITY                       │
│         [ File Sink (NDJSON) ]  [ Pipeline Monitor ]   │
└─────────────────────────────────────────────────────────┘
```

---

## What's Included

### `NormalizedEvent` — Common Schema
ECS-inspired Pydantic model that every source maps to. Captures `timestamp`, `source_type`, `source_ip`, `dest_ip`, `user`, `action`, `outcome`, `severity`, `raw`, `tags`, and a freeform `extra` dict for source-specific fields.

### `SchemaRegistry` — Data Quality Enforcer
Register expected fields per source type. Incoming events that fail validation are quarantined (not dropped), tracked, and available for inspection. Prevents silent data corruption downstream.

### `SyslogSource` — UDP/TCP Listener
Asyncio datagram endpoint for RFC 3164 / 5424 syslog. Runs on an unprivileged port (default `5514`) for MVP. Drop in `syslog-rfc5424-parser` for stricter compliance.

### `CloudTrailSource` — AWS S3 Poller
Watermark-tracked S3 poller for CloudTrail log files. Handles gzip decompression and paginated listing. Maps CloudTrail fields to `NormalizedEvent` automatically.

### `FileSink` — Batched NDJSON Writer
MVP sink that buffers events and flushes to newline-delimited JSON files. Swap for a Kafka producer or S3 multipart upload when volume justifies it.

### `PipelineMonitor` — Gap Detection
Tracks last-seen timestamp and throughput per source. Fires a warning log if any source goes silent beyond a configurable threshold (default: 5 minutes). Prometheus-ready — expose `summary()` as a `/metrics` endpoint.

---

## Quickstart

```bash
# 1. Clone and install dependencies
git clone https://github.com/your-org/sec-pipeline
cd sec-pipeline
pip install -r requirements.txt

# 2. Run the pipeline
python main.py

# 3. Send a test syslog event
echo "<34>Oct 11 22:14:15 mymachine su: 'su root' failed for user on /dev/pts/8" \
  | nc -u 127.0.0.1 5514
```

Events will appear as NDJSON files under `./output/events/`.

---

## Configuration

All config lives in `main.py` for MVP simplicity. Key knobs:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SyslogSource.port` | `5514` | UDP listener port |
| `FileSink.output_dir` | `./output/events` | Output directory |
| `FileSink._flush_every` | `100` | Batch size before flush |
| `PipelineMonitor.gap_threshold_seconds` | `300` | Silence threshold before alert |
| `asyncio.Queue.maxsize` | `10_000` | Max in-flight events |

---

## Requirements

```
pydantic>=2.0
boto3
fastapi
uvicorn
```

```bash
pip install -r requirements.txt
```

Python 3.11+ recommended for asyncio performance improvements.

---

## Project Structure

```
sec-pipeline/
├── ingest/
│   ├── sources/
│   │   ├── syslog.py          # RFC 3164/5424 UDP listener
│   │   ├── cloudtrail.py      # AWS CloudTrail S3 poller
│   │   └── webhook.py         # Generic HTTP webhook receiver
│   ├── queue.py               # Queue abstraction
│   └── sink.py                # FileSink + future Kafka/S3 sinks
├── schema/
│   ├── models.py              # NormalizedEvent Pydantic model
│   └── registry.py            # Schema registry + quarantine
├── health/
│   └── monitor.py             # Gap detection + throughput tracking
├── main.py                    # Entry point + wiring
├── requirements.txt
└── README.md
```

---

## Adding a New Source

1. Create `ingest/sources/your_source.py` and yield `NormalizedEvent` objects
2. Register a `SourceSchema` in `main.py` with required fields
3. Wire it into the queue in `main.py`

That's it. The validation, monitoring, and sink layers pick it up automatically.

---

## Roadmap

- [ ] Swap `FileSink` → Kafka producer
- [ ] Add gRPC receiver for Go collector agent
- [ ] Expose `/metrics` endpoint (Prometheus)
- [ ] Add S3 multipart upload sink
- [ ] Plug in Rust parser for CEF/LEEF formats
- [ ] Dead letter queue for quarantined events
- [ ] Schema versioning + migration support

---

## Security Notes

- This pipeline ingests **untrusted data** — validate inputs at the source layer
- Never log full raw events in production without scrubbing PII
- Run the syslog listener behind a firewall; do not expose it publicly
- Rotate output files and enforce retention policies before writing to shared storage

---

## License

Private — internal use only. Do not distribute.
## License

Private — internal use only. Do not distribute.
