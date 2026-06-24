"""End-to-end API tests with the in-process TestClient (no external services)."""
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_memory_crud_api():
    created = client.post("/memory", json={"content": "API test memory", "type": "task_note", "tags": ["x"]}).json()
    mid = created["id"]
    assert client.get("/memory").status_code == 200
    found = client.get("/memory/search", params={"q": "API test"}).json()
    assert any(m["id"] == mid for m in found)
    upd = client.patch(f"/memory/{mid}", json={"importance": 0.9}).json()
    assert upd["importance"] == 0.9
    assert client.delete(f"/memory/{mid}").json()["deleted"] == mid
    assert client.delete(f"/memory/{mid}").status_code == 404


def test_files_ingest_search_delete_api():
    files = {"file": ("doc.md", b"The mascot is a fox named Pip.", "text/markdown")}
    ing = client.post("/files/ingest", files=files).json()
    fid = ing["file_id"]
    assert ing["num_chunks"] >= 1
    sr = client.post("/files/search", json={"query": "mascot name"}).json()
    assert sr["chunks"]
    assert client.delete(f"/files/{fid}").json()["deleted"] == fid


def test_files_unsupported_type():
    files = {"file": ("x.png", b"\x89PNG", "image/png")}
    r = client.post("/files/ingest", files=files)
    assert r.status_code == 400


def test_chat_degrades_without_model():
    r = client.post("/chat", json={"message": "hello", "mode": "fast"})
    assert r.status_code == 200
    body = r.json()
    # No Ollama in tests -> graceful low-confidence setup message.
    assert body["confidence"] == "low"
    assert "model" in body["answer"].lower()


def test_settings_get_hides_secrets():
    r = client.get("/settings").json()
    assert "secrets_configured" in r
    assert r["enable_cloud_mode"] is False


def test_settings_rejects_unknown_key():
    r = client.post("/settings", json={"updates": {"not_a_real_setting": "x"}})
    assert r.status_code == 400


def test_web_search_unavailable_returns_503(monkeypatch):
    # Force the provider to be unavailable.
    from app.web import search_providers

    class _Null(search_providers.NullProvider):
        pass

    monkeypatch.setattr(search_providers, "get_search_provider", lambda *a, **k: _Null("offline"))
    # Also patch where api.web imported it
    import app.api.web as web_api
    monkeypatch.setattr(web_api, "get_search_provider", lambda *a, **k: _Null("offline"))
    r = client.post("/web/search", json={"query": "test"})
    assert r.status_code == 503
