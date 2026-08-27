"""
MCP Security Gateway — Production Server

Real integration with mcp_monitor package.
Replaces stub that returned {error: "implementation_not_bundled"}.
"""

import logging
import time
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Real integration imports
from mcp_monitor import __version__ as MCP_MONITOR_VERSION
from mcp_monitor.core import MCPSecurityMonitor
from mcp_monitor.models import (
    CallInspection,
    Verdict,
    VerdictLevel,
    PolicyViolation,
    RiskIndicator,
)
from mcp_monitor.policies import PolicyEngine, PolicySet
from mcp_monitor.session import SessionTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Security Gateway Service",
    version=MCP_MONITOR_VERSION,
    description="Inspects MCP (Model Context Protocol) calls for security violations.",
)

# --- Initialize Monitor ---

# Load default policy set and initialize the monitor
_policy_engine = PolicyEngine(PolicySet.default())
_monitor = MCPSecurityMonitor(policy_engine=_policy_engine)
_session_tracker = SessionTracker()
_start_time = time.time()

# --- Request / Response Models ---


class MCPCallRequest(BaseModel):
    """An MCP call to inspect for security issues."""

    session_id: Optional[str] = Field(default=None, description="Session identifier for tracking")
    method: str = Field(..., description="MCP method being called (e.g., 'tools/call', 'resources/read')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Call parameters")
    caller: Optional[str] = Field(default=None, description="Identifier of the calling agent/client")
    target_server: Optional[str] = Field(default=None, description="Target MCP server identifier")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for policy evaluation")


class VerdictResponse(BaseModel):
    """Security verdict for an inspected call."""

    inspection_id: str
    verdict: str
    level: str
    allowed: bool
    risk_score: float
    violations: List[Dict[str, Any]]
    risk_indicators: List[Dict[str, Any]]
    recommendations: List[str]
    duration_ms: float
    metadata: Dict[str, Any]


class PolicyUpdateRequest(BaseModel):
    """Request to update active policies."""

    policy_set: str = Field(..., description="Policy set name to activate")
    custom_rules: Optional[List[Dict[str, Any]]] = Field(default=None, description="Custom rules to add")


class SessionSummaryResponse(BaseModel):
    """Summary of a monitored session."""

    session_id: str
    call_count: int
    violations_count: int
    risk_trend: str
    blocked_calls: int
    duration_seconds: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    monitor_version: str
    active_policies: int
    active_sessions: int
    uptime_seconds: float


# --- Endpoints ---


@app.get("/health", response_model=HealthResponse)
async def health():
    """Return real monitor version and status."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        monitor_version=MCP_MONITOR_VERSION,
        active_policies=_policy_engine.policy_count,
        active_sessions=_session_tracker.active_count,
        uptime_seconds=round(time.time() - _start_time, 2),
    )


@app.post("/inspect", response_model=VerdictResponse)
async def inspect_call(call: MCPCallRequest, request: Request):
    """
    Inspect an MCP call for security violations.

    Runs the call through MCPSecurityMonitor.inspect_call() which evaluates
    all active policies and returns a security verdict.
    """
    inspect_start = time.time()
    inspection_id = f"insp-{int(inspect_start * 1000)}"

    logger.info(
        f"[{inspection_id}] Inspecting call: method={call.method}, "
        f"caller={call.caller}, target={call.target_server}"
    )

    try:
        # Build inspection request for the monitor
        inspection = CallInspection(
            method=call.method,
            params=call.params,
            caller=call.caller,
            target_server=call.target_server,
            context=call.context or {},
            session_id=call.session_id,
        )

        # Run inspection through the real monitor
        verdict: Verdict = _monitor.inspect_call(inspection)

        # Track in session if session_id provided
        if call.session_id:
            _session_tracker.record(
                session_id=call.session_id,
                inspection_id=inspection_id,
                verdict=verdict,
            )

        # Serialize violations
        violations = []
        for v in verdict.violations:
            violations.append({
                "policy_id": v.policy_id,
                "rule_id": v.rule_id,
                "severity": v.severity,
                "description": v.description,
                "evidence": v.evidence,
                "remediation": v.remediation,
            })

        # Serialize risk indicators
        risk_indicators = []
        for ri in verdict.risk_indicators:
            risk_indicators.append({
                "indicator": ri.name,
                "category": ri.category,
                "weight": ri.weight,
                "detail": ri.detail,
            })

        duration_ms = round((time.time() - inspect_start) * 1000, 2)

        logger.info(
            f"[{inspection_id}] Verdict: {verdict.level.value}, "
            f"allowed={verdict.allowed}, risk_score={verdict.risk_score}, "
            f"violations={len(violations)}, duration={duration_ms}ms"
        )

        return VerdictResponse(
            inspection_id=inspection_id,
            verdict=verdict.summary,
            level=verdict.level.value,
            allowed=verdict.allowed,
            risk_score=verdict.risk_score,
            violations=violations,
            risk_indicators=risk_indicators,
            recommendations=verdict.recommendations,
            duration_ms=duration_ms,
            metadata={
                "monitor_version": MCP_MONITOR_VERSION,
                "policies_evaluated": verdict.policies_evaluated,
                "method": call.method,
                "session_id": call.session_id,
            },
        )

    except ValueError as e:
        logger.error(f"[{inspection_id}] Invalid request: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid inspection request: {str(e)}")

    except Exception as e:
        logger.error(f"[{inspection_id}] Inspection failed: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Inspection failed: {str(e)}",
        )


@app.post("/inspect/batch")
async def inspect_batch(calls: List[MCPCallRequest]):
    """Inspect multiple MCP calls, returning verdicts for each."""
    results = []
    for call in calls:
        try:
            inspection = CallInspection(
                method=call.method,
                params=call.params,
                caller=call.caller,
                target_server=call.target_server,
                context=call.context or {},
                session_id=call.session_id,
            )
            verdict: Verdict = _monitor.inspect_call(inspection)
            results.append({
                "method": call.method,
                "verdict": verdict.level.value,
                "allowed": verdict.allowed,
                "risk_score": verdict.risk_score,
                "violation_count": len(verdict.violations),
            })
        except Exception as e:
            results.append({
                "method": call.method,
                "verdict": "error",
                "allowed": False,
                "error": str(e),
            })

    return {
        "batch_size": len(calls),
        "results": results,
        "summary": {
            "total": len(results),
            "allowed": sum(1 for r in results if r.get("allowed", False)),
            "blocked": sum(1 for r in results if not r.get("allowed", True)),
            "errors": sum(1 for r in results if "error" in r),
        },
    }


@app.post("/policies/update")
async def update_policies(update: PolicyUpdateRequest):
    """Update active policy configuration."""
    global _policy_engine, _monitor

    try:
        new_policy_set = PolicySet.load(update.policy_set)

        if update.custom_rules:
            for rule in update.custom_rules:
                new_policy_set.add_rule(rule)

        _policy_engine = PolicyEngine(new_policy_set)
        _monitor = MCPSecurityMonitor(policy_engine=_policy_engine)

        logger.info(f"Policies updated to set: {update.policy_set}")
        return {
            "status": "updated",
            "policy_set": update.policy_set,
            "policy_count": _policy_engine.policy_count,
            "custom_rules_added": len(update.custom_rules) if update.custom_rules else 0,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Policy update failed: {str(e)}")


@app.get("/sessions/{session_id}", response_model=SessionSummaryResponse)
async def session_summary(session_id: str):
    """Get summary of a monitored session."""
    summary = _session_tracker.get_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return SessionSummaryResponse(
        session_id=session_id,
        call_count=summary.call_count,
        violations_count=summary.violations_count,
        risk_trend=summary.risk_trend,
        blocked_calls=summary.blocked_calls,
        duration_seconds=summary.duration_seconds,
    )


@app.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    """End and clean up a monitored session."""
    removed = _session_tracker.end_session(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {"status": "ended", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
