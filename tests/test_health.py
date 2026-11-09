from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_modules_endpoint() -> None:
    response = client.get("/api/modules")
    assert response.status_code == 200
    assert "modules" in response.json()


def test_frontend_is_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "WEB-Constructor" in response.text
