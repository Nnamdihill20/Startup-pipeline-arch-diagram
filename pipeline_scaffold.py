"""
=============================================================
  Cybersecurity Ingestion Pipeline — MVP Starter Scaffold
=============================================================

Stack:
  - Python  : ingestion orchestration, schema validation, health checks
  - Go      : high-throughput event collector (see collector/)
  - Rust    : log parser / normalizer (see parser/)

Project layout:
  pipeline/
  ├── ingest/
  │   ├── __init__.py
  │   ├── sources/
  │   │   ├── syslog.py          # Syslog UDP/TCP listener
  │   │   ├── cloudtrail.py      # AWS CloudTrail poller
  │   │   └── webhook.py         # Generic webhook receiver
  │   ├── normalizer.py          # Schema normalization
  │   ├── queue.py               # Internal event queue abstraction
  │   └── sink.py                # Writes to S3 / local / Kafka
  ├── schema/
  │   ├── registry.py            # Schema registry
  │   └── models.py              # Pydantic event models
  ├── health/
  │   └── monitor.py             # Gap detection + alerting
  └── main.py                    # Entry point
"""

# ─────────────────────────────────────────────
# schema/models.py
# ─────────────────────────────────────────────
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
import uuid


class Severity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


class NormalizedEvent(BaseModel):
    """
    Common schema for all ingested security events.
    Loosely inspired by Elastic Common Schema (ECS).
    """
    event_id:    str      = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:   datetime
    source_type: str                        # e.g. "aws_cloudtrail", "syslog", "edr"
    source_host: Optional[str] = None
    source_ip:   Optional[str] = None
    dest_ip:     Optional[str] = None
    severity:    Severity = Severity.UNKNOWN
    action:      Optional[str] = None       # e.g. "login", "file_write", "network_connect"
    outcome:     Optional[str] = None       # "success" | "failure" | "unknown"
    user:        Optional[str] = None
    process:     Optional[str] = None
    raw:         str = ""                   # Original unparsed log line
    tags:        list[str] = Field(default_factory=list)
    extra:       dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


# ─────────────────────────────────────────────
# schema/registry.py
# ─────────────────────────────────────────────
from dataclasses import dataclass, field


@dataclass
class SourceSchema:
    source_type:      str
    required_fields:  list[str]
    optional_fields:  list[str] = field(default_factory=list)
    description:      str = ""


class SchemaRegistry:
    """
    Lightweight schema registry. Validates that incoming events from a given
    source contain the expected fields. Quarantines malformed records.
    """
    def __init__(self):
        self._schemas: dict[str, SourceSchema] = {}
        self._quarantine: list[dict] = []
        self._stats: dict[str, dict] = {}

    def register(self, schema: SourceSchema):
        self._schemas[schema.source_type] = schema
        self._stats[schema.source_type] = {"valid": 0, "quarantined": 0}

    def validate(self, event: NormalizedEvent) -> bool:
        schema = self._schemas.get(event.source_type)
        if not schema:
            # Unknown source type — pass through with a tag
            event.tags.append("unregistered_source")
            return True

        missing = [
            f for f in schema.required_fields
            if not getattr(event, f, None) and f not in event.extra
        ]

        if missing:
            self._quarantine.append({
                "event_id": event.event_id,
                "source_type": event.source_type,
                "missing_fields": missing,
                "raw": event.raw,
            })
            self._stats[event.source_type]["quarantined"] += 1
            return False

        self._stats[event.source_type]["valid"] += 1
        return True

    def quarantine_log(self) -> list[dict]:
        return self._quarantine

    def stats(self) -> dict:
        return self._stats


# ─────────────────────────────────────────────
# ingest/sources/syslog.py
# ─────────────────────────────────────────────
import asyncio
import logging
from datetime import timezone

logger = logging.getLogger(__name__)


class SyslogSource:
    """
    Listens for syslog messages over UDP on a given port.
    Parses RFC 3164 / 5424 and emits NormalizedEvents.
    For MVP: basic parsing, extend with a proper syslog library later.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 514, queue=None):
        self.host  = host
        self.port  = port
        self.queue = queue  # asyncio.Queue

    async def start(self):
        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _SyslogProtocol(self.queue),
            local_addr=(self.host, self.port),
        )
        logger.info(f"Syslog listener started on {self.host}:{self.port}")
        return transport

    @staticmethod
    def _parse_line(raw: str) -> dict:
        """Minimal RFC 3164 parser. Replace with `syslog-rfc5424-parser` in prod."""
        now = datetime.now(timezone.utc)
        parts = raw.split(" ", 4)
        return {
            "timestamp": now,
            "source_type": "syslog",
            "source_host": parts[3] if len(parts) > 3 else None,
            "process": parts[4].split(":")[0] if len(parts) > 4 else None,
            "action": "log_entry",
            "raw": raw,
        }


class _SyslogProtocol(asyncio.DatagramProtocol):
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    def datagram_received(self, data: bytes, addr):
        raw = data.decode("utf-8", errors="replace").strip()
        parsed = SyslogSource._parse_line(raw)
        try:
            event = NormalizedEvent(**parsed)
            self.queue.put_nowait(event)
        except Exception as e:
            logger.warning(f"Failed to parse syslog event from {addr}: {e}")


# ─────────────────────────────────────────────
# ingest/sources/cloudtrail.py
# ─────────────────────────────────────────────
import json
import gzip
import boto3
from datetime import timezone


class CloudTrailSource:
    """
    Polls an S3 bucket for new CloudTrail log files and emits NormalizedEvents.
    Tracks a watermark to avoid reprocessing.

    Usage:
        source = CloudTrailSource(bucket="my-trail-bucket", prefix="AWSLogs/")
        async for event in source.poll():
            await queue.put(event)
    """
    def __init__(self, bucket: str, prefix: str = "", region: str = "us-east-1"):
        self.bucket  = bucket
        self.prefix  = prefix
        self._seen:  set[str] = set()
        self._s3     = boto3.client("s3", region_name=region)

    async def poll(self):
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key in self._seen:
                    continue
                self._seen.add(key)
                yield from self._process_object(key)

    def _process_object(self, key: str):
        response = self._s3.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"].read()
        if key.endswith(".gz"):
            body = gzip.decompress(body)

        records = json.loads(body).get("Records", [])
        for r in records:
            yield NormalizedEvent(
                timestamp   = datetime.fromisoformat(
                    r["eventTime"].replace("Z", "+00:00")
                ),
                source_type = "aws_cloudtrail",
                source_ip   = r.get("sourceIPAddress"),
                source_host = r.get("userAgent"),
                user        = r.get("userIdentity", {}).get("arn"),
                action      = r.get("eventName"),
                outcome     = "success" if not r.get("errorCode") else "failure",
                severity    = Severity.LOW,
                raw         = json.dumps(r),
                extra       = {
                    "event_source": r.get("eventSource"),
                    "region":       r.get("awsRegion"),
                    "error_code":   r.get("errorCode"),
                },
            )


# ─────────────────────────────────────────────
# ingest/sink.py
# ─────────────────────────────────────────────
import os
import json
import asyncio
from pathlib import Path


class FileSink:
    """
    MVP sink: writes normalized events as newline-delimited JSON.
    Rotate to S3/Kafka when ready.
    """
    def __init__(self, output_dir: str = "./events"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []
        self._flush_every = 100  # events

    async def write(self, event: NormalizedEvent):
        self._buffer.append(event.to_dict())
        if len(self._buffer) >= self._flush_every:
            await self.flush()

    async def flush(self):
        if not self._buffer:
            return
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"events_{date_str}.ndjson"
        with open(path, "a") as f:
            for record in self._buffer:
                f.write(json.dumps(record) + "\n")
        self._buffer.clear()


# ─────────────────────────────────────────────
# health/monitor.py
# ─────────────────────────────────────────────
import time
import logging

logger = logging.getLogger(__name__)


class PipelineMonitor:
    """
    Tracks event throughput per source. Fires an alert if a source
    goes silent for longer than `gap_threshold_seconds`.
    """
    def __init__(self, gap_threshold_seconds: int = 600):
        self._last_seen:  dict[str, float] = {}
        self._counts:     dict[str, int]   = {}
        self._gap_thresh  = gap_threshold_seconds

    def record(self, event: NormalizedEvent):
        src = event.source_type
        self._last_seen[src] = time.time()
        self._counts[src]    = self._counts.get(src, 0) + 1

    def check_gaps(self) -> list[str]:
        """Returns list of sources that have gone silent."""
        now     = time.time()
        silent  = []
        for src, last in self._last_seen.items():
            if now - last > self._gap_thresh:
                silent.append(src)
                logger.warning(
                    f"[ALERT] Source '{src}' silent for "
                    f"{int(now - last)}s (threshold: {self._gap_thresh}s)"
                )
        return silent

    def summary(self) -> dict:
        now = time.time()
        return {
            src: {
                "total_events": self._counts.get(src, 0),
                "seconds_since_last": round(now - ts, 1),
                "status": "ok" if now - ts < self._gap_thresh else "SILENT",
            }
            for src, ts in self._last_seen.items()
        }


# ─────────────────────────────────────────────
# main.py
# ─────────────────────────────────────────────
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_queue(
    queue:    asyncio.Queue,
    registry: SchemaRegistry,
    sink:     FileSink,
    monitor:  PipelineMonitor,
):
    """Core consumer loop: validate → monitor → sink."""
    while True:
        event: NormalizedEvent = await queue.get()
        monitor.record(event)
        if registry.validate(event):
            await sink.write(event)
        else:
            logger.warning(f"Quarantined event {event.event_id} from {event.source_type}")
        queue.task_done()


async def main():
    queue    = asyncio.Queue(maxsize=10_000)
    registry = SchemaRegistry()
    sink     = FileSink(output_dir="./output/events")
    monitor  = PipelineMonitor(gap_threshold_seconds=300)

    # Register known source schemas
    registry.register(SourceSchema(
        source_type     = "aws_cloudtrail",
        required_fields = ["timestamp", "source_ip", "action", "user"],
        description     = "AWS CloudTrail management events",
    ))
    registry.register(SourceSchema(
        source_type     = "syslog",
        required_fields = ["timestamp", "source_host"],
        description     = "RFC 3164/5424 syslog",
    ))

    # Start sources
    syslog_source = SyslogSource(port=5514, queue=queue)  # unprivileged port for MVP
    transport = await syslog_source.start()

    # Start consumer
    consumer = asyncio.create_task(
        process_queue(queue, registry, sink, monitor)
    )

    logger.info("Pipeline running. Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(60)
            print("\n── Pipeline Health ──")
            for src, stats in monitor.summary().items():
                print(f"  {src}: {stats}")
            print(f"  Schema quarantine: {len(registry.quarantine_log())} events")
    except asyncio.CancelledError:
        pass
    finally:
        transport.close()
        await sink.flush()
        consumer.cancel()


if __name__ == "__main__":
    asyncio.run(main())
