from io import BytesIO

from PIL import Image

from fastapi.testclient import TestClient

from backend.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rejects_unsupported_upload():
    with TestClient(app) as client:
        response = client.post("/api/v1/cases", files={"upload": ("unsafe.exe", b"not media", "application/octet-stream")})
    assert response.status_code == 415


def test_image_intake_creates_chain_of_custody():
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "navy").save(buffer, format="PNG")
    png = buffer.getvalue()
    with TestClient(app) as client:
        response = client.post("/api/v1/cases", files={"upload": ("sample.png", png, "image/png")})
        assert response.status_code == 201
        payload = response.json()
        detail = client.get(f"/api/v1/cases/{payload['case_id']}")
    assert len(payload["media"]["original_sha256"]) == 64
    assert payload["media"]["original_sha256"] == payload["media"]["processed_sha256"]
    assert payload["media"]["modality_type"] == "image"
    assert payload["media"]["has_video"] is False
    assert detail.status_code == 200


def test_rejects_corrupt_image_before_creating_case():
    with TestClient(app) as client:
        response = client.post("/api/v1/cases", files={"upload": ("broken.png", b"not an image", "image/png")})
    assert response.status_code == 422
    assert "invalid or corrupted" in response.json()["detail"]
