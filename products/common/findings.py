"""Normalized finding schema shared by product services and the gateway.

Every product service emits findings in this single shape so the gateway can
aggregate, de-duplicate, and correlate signals across tools. The schema is
intentionally small and stable: it is the contract the correlation endpoint
depends on.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

# Canonical severity ordering (used for sorting/aggregation).
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _confidence_to_severity(confidence: str) -> str:
    """Map a detector confidence label to a canonical severity."""
    return {
        "High": "high",
        "Medium": "medium",
        "Low": "low",
    }.get(confidence, "info")


class Finding(BaseModel):
    """A single normalized security finding.

    The `fingerprint` is a deterministic hash of the identifying fields so the
    gateway can de-duplicate identical findings reported by more than one
    service without depending on wall-clock time.
    """

    source: str = Field(description="Product service that produced the finding.")
    rule_id: str = Field(description="Stable identifier for the detection rule.")
    severity: str = Field(description="critical|high|medium|low|info")
    title: str
    technique: str | None = Field(default=None, description="ATT&CK technique, if applicable.")
    tactic: str | None = None
    matrix: str | None = None
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    detected_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def fingerprint(self) -> str:
        raw = f"{self.source}|{self.rule_id}|{self.technique}|{self.title}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class ScanRequest(BaseModel):
    """Untrusted scan input. Bounded to prevent resource exhaustion."""

    content: str = Field(min_length=1, max_length=200_000)


class ScanResponse(BaseModel):
    source: str
    finding_count: int
    findings: list[Finding]


def findings_from_attack_analysis(source: str, analysis: dict[str, Any]) -> list[Finding]:
    """Convert an attack_v19_detector AnalysisResult into normalized findings."""
    findings: list[Finding] = []
    for det in analysis.get("detections", []):
        technique = det.get("technique")
        sub = det.get("sub_technique")
        # Derive a stable rule id from the technique id embedded in the label.
        rule_id = (sub or technique or "UNKNOWN").split()[-1]
        findings.append(
            Finding(
                source=source,
                rule_id=rule_id,
                severity=_confidence_to_severity(det.get("confidence", "")),
                title=det.get("technique", "ATT&CK detection"),
                technique=technique,
                tactic=det.get("tactic"),
                matrix=det.get("matrix"),
                evidence=list(det.get("evidence", [])),
                recommended_action=det.get("recommended_action"),
            )
        )
    return findings
