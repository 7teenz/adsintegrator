import logging
from logging.config import dictConfig


class _DefaultContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key in [
            "request_id",
            "task_id",
            "user_id",
            "job_id",
            "audit_run_id",
            "code",
            "method",
            "path",
            "status_code",
        ]:
            if not hasattr(record, key):
                setattr(record, key, "-")
        return True


def configure_logging(level: str = "INFO") -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "defaults": {
                    "()": "app.logging_config._DefaultContextFilter",
                }
            },
            "formatters": {
                "structured": {
                    "format": (
                        "%(asctime)s %(levelname)s service=meta_ads_audit component=%(name)s event=%(message)s "
                        "request_id=%(request_id)s task_id=%(task_id)s user_id=%(user_id)s "
                        "job_id=%(job_id)s audit_run_id=%(audit_run_id)s code=%(code)s "
                        "method=%(method)s path=%(path)s status_code=%(status_code)s"
                    ),
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "structured",
                    "filters": ["defaults"],
                    "level": level,
                }
            },
            "root": {
                "handlers": ["default"],
                "level": level,
            },
        }
    )


class ContextLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return msg, kwargs


def get_logger(name: str) -> ContextLoggerAdapter:
    return ContextLoggerAdapter(logging.getLogger(name), {})
