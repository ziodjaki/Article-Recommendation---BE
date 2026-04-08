from fastapi.testclient import TestClient

from app.main import app


def test_recommend_endpoint_valid_payload():
    payload = {
        "title": "AI-based Prediction for Learning Outcomes in Hybrid Classrooms",
        "abstract": (
            "This study proposes a machine learning framework for hybrid learning analytics, "
            "including predictive modelling, adaptive intervention, and data-driven instructional "
            "decision support for diverse student cohorts across multiple courses."
        ),
    }

    with TestClient(app) as client:
        response = client.post("/recommend", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "recommendations" in body
    assert len(body["recommendations"]) == 3


def test_recommend_endpoint_invalid_payload_returns_422():
    payload = {"title": "short", "abstract": "too short"}

    with TestClient(app) as client:
        response = client.post("/recommend", json=payload)

    assert response.status_code == 422


def test_recommend_endpoint_rejects_extra_fields():
    payload = {
        "title": "AI-based Prediction for Learning Outcomes in Hybrid Classrooms",
        "abstract": (
            "This study proposes a machine learning framework for hybrid learning analytics, "
            "including predictive modelling, adaptive intervention, and data-driven instructional "
            "decision support for diverse student cohorts across multiple courses."
        ),
        "role": "admin",
    }

    with TestClient(app) as client:
        response = client.post("/recommend", json=payload)

    assert response.status_code == 422


def test_health_has_security_headers():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-robots-tag") == "noindex, nofollow"


def test_recommend_rejects_non_json_content_type():
    body = "title=AI-based Prediction&abstract=This should be rejected because it is not JSON"

    with TestClient(app) as client:
        response = client.post(
            "/recommend",
            content=body,
            headers={"Content-Type": "text/plain"},
        )

    assert response.status_code == 415
