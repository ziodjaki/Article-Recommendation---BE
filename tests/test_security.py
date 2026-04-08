from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security import SecurityMiddleware


def _create_test_app(*, trust_proxy_headers: bool = False) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        SecurityMiddleware,
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
        max_request_size_bytes=256,
        trust_proxy_headers=trust_proxy_headers,
    )

    @app.post("/recommend")
    async def recommend() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_rate_limit_blocks_after_threshold():
    app = _create_test_app()
    with TestClient(app) as client:
        first = client.post("/recommend", json={"a": 1})
        second = client.post("/recommend", json={"a": 1})
        third = client.post("/recommend", json={"a": 1})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_payload_size_limit_blocks_large_request():
    app = _create_test_app()
    with TestClient(app) as client:
        payload = {"text": "a" * 10000}
        response = client.post("/recommend", json=payload)

    assert response.status_code == 413


def test_forwarded_header_ignored_when_untrusted_proxy_setting():
    app = _create_test_app(trust_proxy_headers=False)
    with TestClient(app) as client:
        first = client.post("/recommend", json={"a": 1}, headers={"X-Forwarded-For": "10.1.1.1"})
        second = client.post("/recommend", json={"a": 1}, headers={"X-Forwarded-For": "10.2.2.2"})
        third = client.post("/recommend", json={"a": 1}, headers={"X-Forwarded-For": "10.3.3.3"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
