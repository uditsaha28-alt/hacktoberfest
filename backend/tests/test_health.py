from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_unknown_route_uses_contract_error_shape():
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


def test_cors_allows_frontend_origin():
    res = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"