import io
import os
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from attacks.attack_v19_detector import analyze_attack_v19, main, render_text


class AttackV19DetectorTests(unittest.TestCase):
    def test_enterprise_overlapping_detections_and_chain(self):
        text = "\n".join(
            [
                "powershell.exe -EncodedCommand SQBFAFgA",
                "procdump.exe -ma lsass.exe lsass.dmp",
                "postmark.send_email bcc attacker@evil.example for exfiltration",
            ]
        )

        result = analyze_attack_v19(text)

        techniques = {item["technique"] for item in result["detections"]}
        self.assertIn("Command and Scripting Interpreter T1059", techniques)
        self.assertIn("OS Credential Dumping T1003", techniques)
        self.assertIn("Exfiltration Over Alternative Protocol T1048", techniques)
        self.assertIn("technique_chaining", result)

    def test_mobile_and_ics_matrices_are_detected(self):
        text = "\n".join(
            [
                "Android accessibility service captured password overlay login",
                "PLC discover over MODBUS scan from engineering workstation",
                "online edit changed ladder logic while process stayed running",
            ]
        )

        result = analyze_attack_v19(text)

        matrices = {item["matrix"] for item in result["detections"]}
        self.assertIn("Mobile", matrices)
        self.assertIn("ICS", matrices)

    def test_clean_input_reports_full_scope(self):
        result = analyze_attack_v19("normal health check completed successfully")

        self.assertEqual([], result["detections"])
        output = render_text(result)
        self.assertIn("No ATT&CK techniques detected.", output)
        self.assertIn("Enterprise", output)
        self.assertIn("Mobile", output)
        self.assertIn("ICS", output)

    def test_main_json_reads_stdin(self):
        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO("nmap port scan from 10.0.0.5")), redirect_stdout(stdout):
            exit_code = main(["--format", "json"])

        self.assertEqual(0, exit_code)
        result = json.loads(stdout.getvalue())
        self.assertEqual("Network Service Discovery T1046", result["detections"][0]["technique"])

    def test_main_text_reads_file(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("disable defender with Set-MpPreference")
            path = handle.name

        try:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main([path])

            self.assertEqual(0, exit_code)
            self.assertIn("Defense Impairment TA0112", stdout.getvalue())
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
