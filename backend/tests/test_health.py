from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["app"] == "JARVIS-LOCAL"
    assert "model" in data and "search" in data
    # privacy defaults are local-first
    assert data["privacy"]["cloud_enabled"] is False


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["app"] == "JARVIS-LOCAL"


def test_models_endpoint_does_not_crash_without_ollama():
    r = client.get("/models")
    assert r.status_code == 200
    # Either returns models or a clear error, but never 500s.
    assert "provider" in r.json()
