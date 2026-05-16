import json
import logging
import logging.handlers
import os
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from .config import settings


request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_sub_ctx: ContextVar[str] = ContextVar("user_sub", default="-")
user_role_ctx: ContextVar[str] = ContextVar("user_role", default="-")


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.user_sub = user_sub_ctx.get()
        record.user_role = user_role_ctx.get()
        return True


_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "taskName",
    "request_id", "user_sub", "user_role",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_sub": getattr(record, "user_sub", "-"),
            "user_role": getattr(record, "user_role", "-"),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-5s [%(request_id)s %(user_role)s:%(user_sub)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    level = (os.environ.get("LOG_LEVEL") or "INFO").upper()
    use_json = (os.environ.get("LOG_JSON") or "1").lower() not in ("0", "false", "no")

    log_dir = Path(settings.LOG_DIR).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    app_log = log_dir / "app.log"
    err_log = log_dir / "app.error.log"

    formatter: logging.Formatter = JsonFormatter() if use_json else TextFormatter()
    ctx_filter = ContextFilter()

    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    file_handler = logging.handlers.RotatingFileHandler(
        app_log, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ctx_filter)
    root.addHandler(file_handler)

    err_handler = logging.handlers.RotatingFileHandler(
        err_log, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    err_handler.setLevel(logging.WARNING)
    err_handler.setFormatter(formatter)
    err_handler.addFilter(ctx_filter)
    root.addHandler(err_handler)

    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(level)
    stream.setFormatter(formatter)
    stream.addFilter(ctx_filter)
    root.addHandler(stream)

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
