from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from benchmarks import portfolio_measure as pm
from products.common.body_limit import RequestBodyLimit
from products.common.security import configure_security


def test_repo_python_command_prefers_windows_venv(tmp_path):
    repo = tmp_path / "repo"
    py = repo / ".venv" / "Scripts" / "python.exe"
    py.parent.mkdir(parents=True)
    py.write_text("", encoding="utf-8")
    command = pm.repo_python_command(repo, ["py", "-3.12", "-m", "pytest", "-q"])
    assert command[0] == str(py)
    assert command[1:] == ["-m", "pytest", "-q"]


def test_repo_python_command_leaves_non_python_command(tmp_path):
    command = ["docker", "compose", "config"]
    assert pm.repo_python_command(tmp_path, command) is command


def test_prepend_venv_path(tmp_path):
    scripts = tmp_path / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    env = {"PATH": "base"}
    pm.prepend_venv_path(tmp_path, env)
    assert env["PATH"].startswith(str(scripts) + os.pathsep)


def test_run_check_pass_and_pytest_summary(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    check = pm.Check("id", "repo", "purpose", ["echo", "ok"])

    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="3 passed in 0.1s\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = pm.run_check(tmp_path, check)
    assert result["status"] == "PASS"
    assert "3 passed" in result["pytest_summary"]


def test_run_check_failure_and_timeout(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    check = pm.Check("id", "repo", "purpose", ["cmd"], timeout_s=1)

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=2, stdout="", stderr="boom"),
    )
    failed = pm.run_check(tmp_path, check)
    assert failed["status"] == "FAIL"
    assert failed["returncode"] == 2

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["cmd"], timeout=1, output="partial", stderr="late")

    monkeypatch.setattr(subprocess, "run", timeout)
    timed = pm.run_check(tmp_path, check)
    assert timed["status"] == "FAIL"
    assert timed["returncode"] == 124
    assert timed["timed_out"] is True


def test_write_report_records_scope_and_results(tmp_path):
    report = tmp_path / "report.md"
    raw = tmp_path / "evidence.json"
    results = [
        {
            "repo_id": "repo-a",
            "repo_dir": "repo-a",
            "purpose": "security regression",
            "command": ["py", "-m", "pytest"],
            "timeout_s": 30,
            "returncode": 0,
            "status": "PASS",
            "duration_ms": 12,
            "timed_out": False,
            "pytest_summary": "2 passed",
            "stdout_tail": "ok",
            "stderr_tail": "",
        },
        {
            "repo_id": "repo-b",
            "repo_dir": "repo-b",
            "purpose": "negative path",
            "command": ["cmd"],
            "timeout_s": 30,
            "returncode": 1,
            "status": "FAIL",
            "duration_ms": 5,
            "timed_out": False,
            "pytest_summary": "1 failed",
            "stdout_tail": "",
            "stderr_tail": "failed",
        },
    ]
    pm.write_report(results, report, raw)
    text = report.read_text(encoding="utf-8")
    assert "Passed: 1" in text
    assert "Failed: 1" in text
    assert "does not measure market superiority" in text.lower()
    assert "repo-a" in text and "repo-b" in text


def test_main_writes_json_and_report(tmp_path, monkeypatch):
    root = tmp_path / "repos"
    root.mkdir()
    repo8 = Path(pm.__file__).resolve().parents[1]
    json_rel = Path("evidence/test_portfolio_measure.json")
    report_rel = Path("docs/test_portfolio_measure.md")
    json_path = repo8 / json_rel
    report_path = repo8 / report_rel
    monkeypatch.setattr(pm, "CHECKS", (pm.Check("only", "repo", "purpose", ["cmd"]),))
    monkeypatch.setattr(
        pm,
        "run_check",
        lambda *_args, **_kwargs: {
            "repo_id": "only",
            "repo_dir": "repo",
            "purpose": "purpose",
            "command": ["cmd"],
            "timeout_s": 1,
            "returncode": 0,
            "status": "PASS",
            "duration_ms": 1,
            "timed_out": False,
            "pytest_summary": "n/a",
            "stdout_tail": "",
            "stderr_tail": "",
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "portfolio_measure",
            "--root",
            str(root),
            "--json",
            str(json_rel),
            "--report",
            str(report_rel),
        ],
    )
    try:
        assert pm.main() == 0
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["results"][0]["status"] == "PASS"
        assert report_path.exists()
    finally:
        json_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)


def test_request_body_limit_rejects_oversized_body():
    app = FastAPI()
    app.add_middleware(RequestBodyLimit, max_bytes=4)

    @app.post("/echo")
    async def echo():
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/echo", content=b"12345")
    assert response.status_code == 413


def test_security_headers_health_and_rate_limit():
    app = FastAPI()
    configure_security(app)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/data")
    async def data():
        return {"ok": True}

    client = TestClient(app)
    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.headers["X-Content-Type-Options"] == "nosniff"
    assert health_response.headers["Cache-Control"] == "no-store"

    for _ in range(60):
        assert client.get("/data").status_code == 200
    assert client.get("/data").status_code == 429
