from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        response: Response = await call_next(request)  # type: ignore[operator]

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        api_key_ctx = getattr(request.state, "api_key_ctx", None)
        client_name = api_key_ctx.client_name if api_key_ctx is not None else "anonymous"
        logger.info(
            "request_id=%s method=%s path=%s client=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            client_name,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
