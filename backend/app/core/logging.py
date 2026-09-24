"""
Structured JSON logging for research and forensic audits.
Outputs standardized forensic log events to stdout and logs/forensic_audit.log.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path
from backend.app.core.config import settings


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge custom forensic extra fields
        if hasattr(record, "forensic_data") and isinstance(record.forensic_data, dict):
            log_payload.update(record.forensic_data)

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def setup_logger(name: str = "forensic_system") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredJsonFormatter())
    logger.addHandler(console_handler)

    # File handler
    log_file = settings.LOGS_DIR / "forensic_audit.log"
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setFormatter(StructuredJsonFormatter())
    logger.addHandler(file_handler)

    return logger


logger = setup_logger("forensic_pipeline")


def log_forensic_event(
    event: str,
    case_id: Optional[str] = None,
    agent: Optional[str] = None,
    latency_ms: Optional[float] = None,
    confidence: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO,
):
    """Utility to emit structured forensic log entries."""
    data: Dict[str, Any] = {
        "event": event,
        "case_id": case_id,
        "agent": agent,
        "latency_ms": latency_ms,
        "confidence": confidence,
    }
    if details:
        data.update(details)

    # Clean None values
    filtered_data = {k: v for k, v in data.items() if v is not None}
    logger.log(level, event, extra={"forensic_data": filtered_data})
