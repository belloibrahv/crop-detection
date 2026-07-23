"""
logging_config.py — Structured JSON logging for the AgroScan NG API.

Emits every log record as a single-line JSON object to stdout so that
Render (and any log aggregator) can parse and index fields.

Fields in every record:
  timestamp, level, logger, message
  + any extra kwargs passed to logger.info(..., extra={...})
"""
import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format a LogRecord as a JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level':     record.levelname,
            'logger':    record.name,
            'message':   record.getMessage(),
        }
        # Include any extra fields passed via extra={} kwarg
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith('_'):
                log_obj[key] = value

        if record.exc_info:
            log_obj['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def configure_logging(app) -> None:
    """
    Replace Flask's default handlers with a single structured JSON handler
    writing to stdout. Call this once inside create_app().
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Root logger — catches everything including SQLAlchemy, werkzeug, etc.
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Suppress noisy werkzeug request logs in production (Gunicorn handles access logs)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    app.logger.info('Structured JSON logging initialised', extra={'service': 'api'})
