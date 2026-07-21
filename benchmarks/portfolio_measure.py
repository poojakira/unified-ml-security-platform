"""Run focused portfolio security measurements across the local repo set.

This runner records what was actually executed. It is intentionally scoped:
it measures focused regression/security checks, not commercial superiority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    repo_id: str
    repo_dir: str
    purpose: str
    command: list[str]
    env: dict[str, str] | None = None
    timeout_s: int = 240


CHECKS: tuple[Check, ...] = (
    Check(
        repo_id="repo1-mcp-security-gateway-monitor",
        repo_dir="repo1-mcp",
        purpose="Prompt-injection normalization and BCC header bypass regression tests.",
        command=["py", "-3.12", "-m", "pytest", "tests/test_normalization_pipeline.py", "tests/test_bcc_normalization.py", "-q"],
    ),
    Check(
        repo_id="repo2-hf-model-provenance-scanner",
        repo_dir="repo2-hf",
        purpose="Pickle magic-byte and scanner regression tests for renamed payload coverage.",
        command=["py", "-3.12", "-m", "pytest", "tests/test_pickle_scanner.py", "-q"],
    ),
    Check(
        repo_id="repo3-PulseNet-RUL-Forecasting",
        repo_dir="repo3-pulsenet",
        purpose="JWT secret hardening and audit-log integrity regression tests.",
        command=["py", "-3.12", "-m", "pytest", "tests/test_auth_secret.py", "tests/test_extra_coverage.py::TestAuditLogger", "-q"],
        env={"PULSENET_JWT_SECRET": "portfolio-measurement-secret-32bytes-minimum"},
    ),
    Check(
        repo_id="repo4-dataset-poisoning-detector",
        repo_dir="repo4-poison",
        purpose="False-positive budget and slow-drift poisoning detection regression tests.",
        command=["py", "-3.12", "-m", "pytest", "tests/test_drift.py", "tests/test_fp_budget.py", "-q"],
    ),
    Check(
        repo_id="repo5-llm-redteam-framework",
        repo_dir="repo5-redteam",
        purpose="LLM classifier false-positive budget enforcement tests.",
        command=["py", "-3.12", "-m", "pytest", "tests/test_fp_budget.py"],
    ),
    Check(
        repo_id="repo6-model-privacy-attacks",
        repo_dir="repo6-privacy",
        purpose="Privacy attack implementation and probability-fidelity regression tests.",
        command=["py", "-3.12", "-m", "pytest", "tests/test_privacy_attacks.py", "-q"],
    ),
    Check(
        repo_id="repo7-adversarial-ml-lab",
        repo_dir="repo7-adv",
        purpose="Benchmark signing and verification integrity tests.",
        command=["py", "-3.12", "-m", "pytest", "tests/test_ci_signing.py", "tests/test_benchmark_verify.py", "-q"],
    ),
    Check(
        repo_id="repo8-unified-ml-security-platform",
        repo_dir="repo8-platform",
        purpose="Architecture-spec service compile validation.",
        command=["py", "-3.12", "-m", "py_compile", "spec_service.py", "gateway_server.py"],
    ),
    Check(
        repo_id="repo8-unified-ml-security-platform-compose",
        repo_dir="repo8-platform",
        purpose="Self-contained docker-compose syntax/config validation.",
        command=["docker", "compose", "-f", "docker-compose.yml", "config"],
        timeout_s=120,
    ),
)

PYTEST_RE = re.compile(r"(?P<summary>(?:\d+\s+passed|\d+\s+failed|\d+\s+skipped|\d+\s+warnings?)[^\n]*)", re.IGNORECASE)


def run_check(root: Path, check: Check) -> dict[str, object]:
    repo_path = root / check.repo_dir
    env = os.environ.copy()
    pythonpath_parts = []
    if (repo_path / "src").exists():
        pythonpath_parts.append(str(repo_path / "src"))
    pythonpath_parts.append(str(repo_path))
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    if check.env:
        env.update(check.env)

    started = time.perf_counter()
    try:
        proc = subprocess.run(
            check.command,
            cwd=repo_path,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=check.timeout_s,
            check=False,
        )
        timed_out = False
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    duration_ms = int((time.perf_counter() - started) * 1000)
    combined = f"{stdout}\n{stderr}"
    summaries = [match.group("summary").strip("= ").strip() for match in PYTEST_RE.finditer(combined)]

    return {
        "repo_id": check.repo_id,
        "repo_dir": check.repo_dir,
        "purpose": check.purpose,
        "command": check.command,
        "timeout_s": check.timeout_s,
        "returncode": returncode,
        "status": "PASS" if returncode == 0 and not timed_out else "FAIL",
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "pytest_summary": summaries[-1] if summaries else "n/a",
        "stdout_tail": "\n".join(stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-20:]),
    }


def write_report(results: list[dict[str, object]], report_path: Path, json_path: Path) -> None:
    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = len(results) - passed
    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    lines = [
        "# Portfolio Measurement Report",
        "",
        f"Generated UTC: {generated}",
        "",
        "## Scope",
        "",
        "This report measures focused security and correctness checks against the local checked-out branches. It does not measure market superiority, production scale, customer telemetry, or independent commercial benchmarks.",
        "",
        "## Summary",
        "",
        f"- Checks run: {len(results)}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Raw JSON evidence: `{json_path.as_posix()}`",
        "",
        "## Results",
        "",
        "| Repo/check | Status | Duration ms | Pytest summary | Purpose |",
        "|---|---:|---:|---|---|",
    ]
    for item in results:
        lines.append(
            "| {repo_id} | {status} | {duration_ms} | {pytest_summary} | {purpose} |".format(
                repo_id=item["repo_id"],
                status=item["status"],
                duration_ms=item["duration_ms"],
                pytest_summary=str(item["pytest_summary"]).replace("|", "\\|"),
                purpose=str(item["purpose"]).replace("|", "\\|"),
            )
        )

    lines.extend([
        "",
        "## Commands Executed",
        "",
    ])
    for item in results:
        command = " ".join(str(part) for part in item["command"])
        lines.extend([
            f"### {item['repo_id']}",
            "",
            f"Working directory: `../{item['repo_dir']}`",
            "",
            "```powershell",
            command,
            "```",
            "",
            f"Exit code: `{item['returncode']}`",
            "",
        ])
        if item["stdout_tail"]:
            lines.extend(["Stdout tail:", "", "```text", str(item["stdout_tail"]), "```", ""])
        if item["stderr_tail"]:
            lines.extend(["Stderr tail:", "", "```text", str(item["stderr_tail"]), "```", ""])

    lines.extend([
        "## Honest Interpretation",
        "",
        "Passing these checks means the local branches satisfy focused regression gates selected for this remediation pass. It does not prove the products are unhackable or better than mature commercial platforms.",
        "",
        "A legitimate commercial comparison still requires independent benchmark corpora, latency and false-positive measurements on production-like benign traffic, SIEM/telemetry verification, supply-chain evidence, and repeated runs across clean environments.",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run focused ML-security portfolio measurements.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2], help="Directory containing repo1-mcp through repo8-platform.")
    parser.add_argument("--json", type=Path, default=Path("evidence/portfolio_measurement_2026-07-21.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/MEASUREMENT_REPORT_2026-07-21.md"))
    args = parser.parse_args()

    repo8 = Path(__file__).resolve().parents[1]
    json_path = (repo8 / args.json).resolve()
    report_path = (repo8 / args.report).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    results = [run_check(args.root.resolve(), check) for check in CHECKS]
    payload = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(args.root.resolve()),
        "scope": "Focused local checked-out branch security and correctness measurements; not market-superiority proof.",
        "results": results,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_report(results, report_path, json_path.relative_to(repo8))

    failed = [item for item in results if item["status"] != "PASS"]
    print(f"wrote {json_path}")
    print(f"wrote {report_path}")
    print(f"passed={len(results) - len(failed)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
