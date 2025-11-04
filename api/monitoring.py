"""Monitoring utilities for logging and metrics."""

from __future__ import annotations

import json
import logging
import time
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response
from prometheus_fastapi_instrumentator import Instrumentator

LOGGER = logging.getLogger("api.requests")


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]]
):
    """Log request/response metadata in a structured JSON format."""

    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    log_payload = {
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "query": request.url.query,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 3),
        "client_host": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
    LOGGER.info(json.dumps(log_payload, ensure_ascii=False))
    response.headers["X-Process-Time"] = f"{duration:.3f}s"
    return response


_instrumentator = Instrumentator()


def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus instrumentation to the FastAPI application."""

    if getattr(app.state, "_metrics_enabled", False):
        return

    _instrumentator.instrument(app)
    _instrumentator.expose(app, include_in_schema=False)
    app.state._metrics_enabled = True