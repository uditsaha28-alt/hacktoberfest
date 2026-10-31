import re

import pytest
from fastapi.testclient import TestClient

from app.agent import fake_run
from app.agent.tools import github_client
from app.agent.tools.github_client import GitHubError
from app.config import settings
from app.main import app
from app.services.repo_url import parse_repo_url


async def _fake_get_repo(owner, name):
    return {"default_branch": "main", "description": "", "language": "Python", "stars": 0, "open_issues": 0}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(fake_run, "STEP_DELAY", 0)
    monkeypatch.setattr(github_client, "get_repo", _fake_get_repo)
    with TestClient(app) as c:
        yield c


def start_run(client):
    res = client.post("/api/runs", json={"repo_url": "https://github.com/pallets/flask"})
    assert res.status_code == 201
    return res.json()["run_id"]


def read_events(client, run_id):
    with client.stream("GET", f"/api/runs/{run_id}/events") as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        body = "".join(res.iter_text())
    return re.findall(r"^event: (\w+)$", body, flags=re.MULTILINE)


def test_parse_repo_url():
    assert parse_repo_url("https://github.com/pallets/flask") == ("pallets", "flask")
    assert parse_repo_url("https://github.com/pallets/flask.git") == ("pallets", "flask")
    assert parse_repo_url("https://github.com/pallets/flask/") == ("pallets", "flask")
    for bad in ["", "not a url", "https://gitlab.com/a/b", "https://github.com/onlyowner"]:
        with pytest.raises(ValueError):
            parse_repo_url(bad)


def test_create_run_rejects_bad_url(client):
    res = client.post("/api/runs", json={"repo_url": "https://example.com/x/y"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_repo_url"


def test_create_run_rejects_missing_body(client):
    res = client.post("/api/runs", json={})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_request"


def test_events_follow_contract_order(client):
    run_id = start_run(client)
    types = read_events(client, run_id)
    assert types[0] == "plan"
    assert types[-1] == "done"
    assert types.count("tool_call") == types.count("observation") > 0
    assert "section" in types
    assert types.count("plan") >= 2  # includes a replan


def test_report_available_after_done(client):
    run_id = start_run(client)
    read_events(client, run_id)
    res = client.get(f"/api/runs/{run_id}/report")
    assert res.status_code == 200
    report = res.json()
    assert set(report) == {"repo", "summary", "sections", "mermaid", "first_issues"}
    assert report["repo"] == "pallets/flask"
    assert all(i["difficulty"] in {"easy", "medium", "hard"} for i in report["first_issues"])


def test_report_unknown_run(client):
    res = client.get("/api/runs/nope/report")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "run_not_found"


def test_report_before_finished(client, monkeypatch):
    monkeypatch.setattr(fake_run, "STEP_DELAY", 0.5)
    run_id = start_run(client)
    res = client.get(f"/api/runs/{run_id}/report")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "run_not_finished"

def test_create_run_repo_not_found(client, monkeypatch):
    async def boom(owner, name):
        raise GitHubError(404, "repo_not_found", "Repository not found or not public.")

    monkeypatch.setattr(github_client, "get_repo", boom)
    res = client.post("/api/runs", json={"repo_url": "https://github.com/nobody/nothing"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "repo_not_found"


def test_create_run_rate_limited(client, monkeypatch):
    async def boom(owner, name):
        raise GitHubError(429, "rate_limited", "GitHub rate limit reached.")

    monkeypatch.setattr(github_client, "get_repo", boom)
    res = client.post("/api/runs", json={"repo_url": "https://github.com/pallets/flask"})
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "rate_limited"


def test_create_run_github_down_maps_to_502(client, monkeypatch):
    async def boom(owner, name):
        raise GitHubError(502, "github_unreachable", "Could not reach GitHub.")

    monkeypatch.setattr(github_client, "get_repo", boom)
    res = client.post("/api/runs", json={"repo_url": "https://github.com/pallets/flask"})
    assert res.status_code == 502