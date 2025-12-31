
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id into every record (if present in context)."""
    def __init__(self, get_correlation_id_callable):
        super().__init__()
        self._get_correlation_id = get_correlation_id_callable

    def filter(self, record):
        cid = self._get_correlation_id()
        record.correlation_id = cid or "-"
        return True

def _json_formatter():
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            import json
            payload = {
                "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
                "correlation_id": getattr(record, "correlation_id", "-"),
            }
            # Include extras if present
            for key in ("pathname", "lineno", "funcName"):
                payload[key] = getattr(record, key, None)
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(payload)
    return JsonFormatter()

def _text_formatter():
    return logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] [cid=%(correlation_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def init_logging(settings: Dict[str, Any], get_correlation_id_callable=lambda: None):
    """Initialize root logging based on settings.yaml and environment variables."""
    cfg = (settings or {}).get("logging") or {}
    level_name = os.getenv("LOG_LEVEL", cfg.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = os.getenv("LOG_FORMAT", cfg.get("format", "json")).lower()
    propagate_cid = bool(cfg.get("propagate_correlation_id", True))

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicate logs on reload
    for h in list(root.handlers):
        root.removeHandler(h)

    # Formatter
    formatter = _json_formatter() if fmt == "json" else _text_formatter()

    # Correlation filter
    cid_filter = CorrelationIdFilter(get_correlation_id_callable) if propagate_cid else None

    # Console handler
    if cfg.get("console", True):
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        if cid_filter:
            ch.addFilter(cid_filter)
        root.addHandler(ch)

    # Rotating file handler (optional)
    fcfg = cfg.get("file", {})
    if fcfg.get("enabled"):
        path = fcfg.get("path", "logs/app.log")
        #print(path)
        max_bytes = int(fcfg.get("max_bytes", 10_485_760))  # 10MB
        backup_count = int(fcfg.get("backup_count", 5))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fh = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        if cid_filter:
            fh.addFilter(cid_filter)
        root.addHandler(fh)

def get_logger(name: str) -> logging.Logger:
    """Get a module-specific logger."""
    return logging.getLogger(name)
