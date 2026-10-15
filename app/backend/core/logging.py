"""Structured logging (JSON lines) via structlog."""

import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    log_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=log_level)
    # The HTTP client logs every request at INFO (Keycloak, connectors, the LLM): noise in the
    # console. Its warnings and errors still show; our own logs say what each call was for.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(max(log_level, logging.WARNING))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    logger: structlog.typing.FilteringBoundLogger = structlog.get_logger(name)
    return logger
