from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
    "X-Robots-Tag": "noindex, nofollow",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        rate_limit_requests: int,
        rate_limit_window_seconds: int,
        max_request_size_bytes: int,
        trust_proxy_headers: bool,
    ):
        super().__init__(app)
        self.rate_limit_requests = max(1, rate_limit_requests)
        self.rate_limit_window_seconds = max(1, rate_limit_window_seconds)
        self.max_request_size_bytes = max(4096, max_request_size_bytes)
        self.trust_proxy_headers = trust_proxy_headers
        self._request_windows: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").strip()
        if self.trust_proxy_headers and forwarded:
            return forwarded.split(",")[0].strip()

        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _rate_limit_key(self, request: Request) -> str:
        path = request.url.path
        method = request.method.upper()
        return f"{self._client_ip(request)}:{method}:{path}"

    def _is_rate_limited(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.rate_limit_window_seconds

        with self._lock:
            q = self._request_windows[key]
            while q and q[0] < window_start:
                q.popleft()
            if len(q) >= self.rate_limit_requests:
                return True
            q.append(now)
            return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/recommend" and request.method.upper() == "POST":
            content_type = request.headers.get("content-type", "")
            if "application/json" not in content_type.lower():
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={"detail": "Content-Type must be application/json"},
                )

            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    declared_size = int(content_length)
                    if declared_size > self.max_request_size_bytes:
                        return JSONResponse(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            content={"detail": "Payload too large"},
                        )
                except ValueError:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Invalid Content-Length header"},
                    )

            raw_body = await request.body()
            if len(raw_body) > self.max_request_size_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={"detail": "Payload too large"},
                )

            if self._is_rate_limited(self._rate_limit_key(request)):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests, please retry later"},
                )

        response = await call_next(request)
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers.setdefault(header_name, header_value)

        if request.url.path == "/recommend":
            response.headers.setdefault("Cache-Control", "no-store")

        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        return response


def _extract_candidate_keys(request: Request) -> list[str]:
    keys: list[str] = []

    x_api_key = request.headers.get("x-api-key", "").strip()
    if x_api_key:
        keys.append(x_api_key)

    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
        if bearer:
            keys.append(bearer)

    return keys


def require_api_key(request: Request) -> None:
    if not settings.enforce_api_key:
        return

    if not settings.api_keys:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API key is not configured")

    candidates = _extract_candidate_keys(request)
    if not candidates:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    for provided_key in candidates:
        for valid_key in settings.api_keys:
            if secrets.compare_digest(provided_key, valid_key):
                return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
