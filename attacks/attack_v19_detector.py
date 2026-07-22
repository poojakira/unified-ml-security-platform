"""MITRE ATT&CK v19 detection contract and seed detector.

This module is intentionally dependency-free. It provides a strict output
contract, framework scope metadata, and deterministic seed rules for portfolio
products. It does not claim exhaustive ML training coverage by itself.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Iterable

ATTACK_VERSION = "ATT&CK v19 (April 28, 2026)"

ENTERPRISE_TACTICS = [
    "Reconnaissance TA0043",
    "Resource Development TA0042",
    "Initial Access TA0001",
    "Execution TA0002",
    "Persistence TA0003",
    "Privilege Escalation TA0004",
    "Stealth TA0005",
    "Defense Impairment TA0112",
    "Credential Access TA0006",
    "Discovery TA0007",
    "Lateral Movement TA0008",
    "Collection TA0009",
    "Command & Control TA0011",
    "Exfiltration TA0010",
    "Impact TA0040",
]

MOBILE_TACTICS = [
    "Initial Access",
    "Execution",
    "Persistence",
    "Privilege Escalation",
    "Defense Evasion",
    "Credential Access",
    "Discovery",
    "Lateral Movement",
    "Collection",
    "Command & Control",
    "Exfiltration",
    "Impact",
]

ICS_TACTICS = [
    "Initial Access",
    "Execution",
    "Persistence",
    "Privilege Escalation",
    "Evasion",
    "Discovery",
    "Lateral Movement",
    "Collection",
    "Command & Control",
    "Inhibit Response Function",
    "Impair Process Control",
    "Impact",
]


@dataclass(frozen=True)
class DetectionRule:
    matrix: str
    tactic: str
    technique: str
    sub_technique: str | None
    confidence: str
    patterns: tuple[str, ...]
    recommended_action: str


RULES: tuple[DetectionRule, ...] = (
    DetectionRule("Enterprise", "Initial Access TA0001", "Phishing T1566", None, "Medium", (r"\bphishing\b", r"\bspearphish", r"\bcredential harvest"), "Quarantine the message, preserve headers, and block sender infrastructure."),
    DetectionRule("Enterprise", "Execution TA0002", "Command and Scripting Interpreter T1059", "PowerShell T1059.001", "High", (r"\bpowershell(\.exe)?\b", r"\b-enc(odedcommand)?\b", r"\bfrombase64string\b"), "Terminate the process, collect command line telemetry, and isolate the host if unauthorized."),
    DetectionRule("Enterprise", "Execution TA0002", "Command and Scripting Interpreter T1059", "Python T1059.006", "High", (r"\bpython(\.exe)?\b", r"\bos\.system\b", r"\bsubprocess\.", r"\beval\("), "Block execution path, capture script or serialized object, and review parent process lineage."),
    DetectionRule("Enterprise", "Initial Access TA0001", "Supply Chain Compromise T1195", "Compromise Software Supply Chain T1195.002", "Medium", (r"\bpickle\b.*\b(os\.system|subprocess|eval)\b", r"\bmalicious model\b", r"\bsafetensors metadata\b"), "Do not load the artifact; quarantine it and require signed, provenance-verified model formats."),
    DetectionRule("Enterprise", "Persistence TA0003", "Boot or Logon Autostart Execution T1547", "Registry Run Keys / Startup Folder T1547.001", "High", (r"\\currentversion\\run\b", r"\bstartup folder\b", r"\bschtasks\b.*\b/create\b"), "Disable the autorun entry, export it for evidence, and rotate credentials used on the host."),
    DetectionRule("Enterprise", "Privilege Escalation TA0004", "Process Injection T1055", None, "Medium", (r"\bprocess injection\b", r"\bcreateremotethread\b", r"\bwriteprocessmemory\b"), "Suspend the process tree, acquire memory, and block the injector hash."),
    DetectionRule("Enterprise", "Stealth TA0005", "Indicator Removal T1070", "Clear Windows Event Logs T1070.001", "High", (r"\bwevtutil\b.*\bcl\b", r"\bclear-eventlog\b", r"\bdelete logs?\b"), "Forward logs from centralized storage, isolate the host, and revoke active sessions."),
    DetectionRule("Enterprise", "Defense Impairment TA0112", "Impair Defenses T1562", "Disable or Modify Tools T1562.001", "High", (r"\bdisable.*defender\b", r"\bset-mppreference\b", r"\btamper protection\b"), "Re-enable controls from EDR console and investigate administrative token use."),
    DetectionRule("Enterprise", "Credential Access TA0006", "OS Credential Dumping T1003", "LSASS Memory T1003.001", "High", (r"\blsass\b", r"\bsekurlsa\b", r"\bprocdump\b.*\blsass\b", r"\bmimikatz\b"), "Isolate the endpoint and rotate credentials for accounts with interactive logons."),
    DetectionRule("Enterprise", "Discovery TA0007", "System Network Configuration Discovery T1016", None, "Medium", (r"\bipconfig\b", r"\bifconfig\b", r"\bnetstat\b", r"\broute print\b"), "Correlate with parent process and restrict follow-on lateral movement paths."),
    DetectionRule("Enterprise", "Discovery TA0007", "Network Service Discovery T1046", None, "High", (r"\bnmap\b", r"\bmasscan\b", r"\bport scan\b"), "Block scanner source and review exposed services found during the scan window."),
    DetectionRule("Enterprise", "Lateral Movement TA0008", "Remote Services T1021", None, "Medium", (r"\bpsexec\b", r"\bwmic\b.*\b/node\b", r"\brdp\b", r"\bssh\b.*\b-i\b"), "Disable the remote session, check peer hosts, and require privileged access review."),
    DetectionRule("Enterprise", "Command & Control TA0011", "Application Layer Protocol T1071", None, "Medium", (r"\bbeacon\b", r"\bcallback\b", r"\bc2\b", r"\bcommand and control\b"), "Block destination infrastructure and inspect proxy, DNS, and TLS metadata."),
    DetectionRule("Enterprise", "Exfiltration TA0010", "Exfiltration Over Alternative Protocol T1048", None, "High", (r"\bbcc\b.*\b(attacker|evil|exfil)\b", r"\bexfiltrat", r"\bhidden_recipient", r"\bblind_copy\b"), "Block the transfer, preserve payload metadata, and rotate exposed secrets."),
    DetectionRule("Enterprise", "Impact TA0040", "Data Encrypted for Impact T1486", None, "High", (r"\bransomware\b", r"\bencrypt(ed|ing)? files\b", r"\brestore from backup\b"), "Contain affected systems, disable shared credentials, and start restore from immutable backups."),
    DetectionRule("Mobile", "Credential Access", "Input Capture T1417", "Keylogging T1417.001", "High", (r"\bkeylog", r"\baccessibility service\b.*\bpassword\b", r"\boverlay\b.*\blogin\b"), "Revoke app permissions, remove the app, and reset credentials entered on the device."),
    DetectionRule("Mobile", "Collection", "Data from Local System T1533", None, "Medium", (r"\bcontacts\b", r"\bsms\b", r"\bcall log\b", r"\blocation history\b"), "Disable app data access and preserve mobile forensic evidence."),
    DetectionRule("Mobile", "Command & Control", "Application Layer Protocol T1437", None, "Medium", (r"\bmobile\b.*\bc2\b", r"\bfirebase\b.*\bcommand\b", r"\bfcm\b.*\bcommand\b"), "Block app backend communication and revoke push notification tokens."),
    DetectionRule("ICS", "Discovery", "Remote System Discovery T0846", "Broadcast Discovery T0846.002", "High", (r"\bmodbus\b.*\bscan\b", r"\bplc\b.*\bdiscover", r"\budp\b.*\b1502\b"), "Segment the engineering network and block unauthorized discovery traffic."),
    DetectionRule("ICS", "Lateral Movement", "Program Download T0843", "Online Edit T0843.002", "High", (r"\bonline edit\b", r"\bprogram download\b", r"\bladder logic\b.*\bupdate\b"), "Stop unauthorized engineering workstation sessions and verify controller logic integrity."),
    DetectionRule("ICS", "Inhibit Response Function", "Modify Alarm Settings T0838", None, "High", (r"\bdisable alarm", r"\balarm threshold\b.*\bchanged\b", r"\binhibit response\b"), "Restore alarm configuration from known-good baseline and validate operator visibility."),
    DetectionRule("ICS", "Impair Process Control", "Unauthorized Command Message T0855", None, "High", (r"\bunauthorized command\b", r"\bsetpoint\b.*\bchanged\b", r"\bopen valve\b", r"\bstop pump\b"), "Place process in safe state and block the unauthorized control path."),
)


def _matching_evidence(text: str, patterns: Iterable[str]) -> list[str]:
    evidence: list[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines or [text.strip()]:
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                evidence.append(line[:300])
                break
    return evidence


def analyze_attack_v19(text: str) -> dict[str, object]:
    """Analyze text and return ATT&CK-formatted detections."""
    detections: list[dict[str, object]] = []
    for rule in RULES:
        evidence = _matching_evidence(text, rule.patterns)
        if evidence:
            detections.append({"tactic": rule.tactic, "technique": rule.technique, "sub_technique": rule.sub_technique, "matrix": rule.matrix, "confidence": rule.confidence, "evidence": evidence, "recommended_action": rule.recommended_action})

    result: dict[str, object] = {"version": ATTACK_VERSION, "scope_covered": {"Enterprise": ENTERPRISE_TACTICS, "Mobile": MOBILE_TACTICS, "ICS": ICS_TACTICS}, "detections": detections}
    if detections:
        result["technique_chaining"] = [f"{item['technique']}" + (f" -> {item['sub_technique']}" if item["sub_technique"] else "") for item in detections]
    else:
        result["status"] = "No ATT&CK techniques detected."
    return result


def render_text(result: dict[str, object]) -> str:
    detections = result.get("detections", [])
    if not detections:
        scope = result["scope_covered"]
        return "No ATT&CK techniques detected. Scope covered: " + "; ".join(f"{matrix}: {', '.join(tactics)}" for matrix, tactics in scope.items())

    blocks: list[str] = []
    for item in detections:
        blocks.append("\n".join([f"Tactic: {item['tactic']}", f"Technique: {item['technique']}", f"Sub-technique: {item['sub_technique'] or 'None'}", f"Matrix: {item['matrix']}", f"Confidence: {item['confidence']}", "Evidence: " + " | ".join(f'"{quote}"' for quote in item["evidence"]), f"Recommended action: {item['recommended_action']}"]))
    chain = result.get("technique_chaining", [])
    if chain:
        blocks.append("Technique chaining: " + " -> ".join(chain))
    return "\n\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze input against ATT&CK v19 seed rules.")
    parser.add_argument("input_file", nargs="?", help="File to analyze. Reads stdin when omitted.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    if args.input_file:
        with open(args.input_file, encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()

    result = analyze_attack_v19(text)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
