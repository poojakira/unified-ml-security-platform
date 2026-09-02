import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from attacks.attack_v19_detector import analyze_attack_v19, main, render_text


class AttackV19DetectorTests(unittest.TestCase):
    def test_enterprise_overlapping_detections_and_chain(self):
        text = "powershell.exe -EncodedCommand SQBFAFgA\nprocdump.exe -ma lsass.exe lsass.dmp\npostmark.send_email bcc attacker@evil.example for exfiltration"

        result = analyze_attack_v19(text)

        techniques = {item["technique"] for item in result["detections"]}
        self.assertIn("Command and Scripting Interpreter T1059", techniques)
        self.assertIn("OS Credential Dumping T1003", techniques)
        self.assertIn("Exfiltration Over Alternative Protocol T1048", techniques)
        self.assertIn("technique_chaining", result)

    def test_mobile_and_ics_matrices_are_detected(self):
        text = "Android accessibility service captured password overlay login\nPLC discover over MODBUS scan from engineering workstation\nonline edit changed ladder logic while process stayed running"

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
        with (
            patch("sys.stdin", io.StringIO("nmap port scan from 10.0.0.5")),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--format", "json"])

        self.assertEqual(0, exit_code)
        result = json.loads(stdout.getvalue())
        self.assertEqual(
            "Network Service Discovery T1046", result["detections"][0]["technique"]
        )

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

    def test_analyze_rejects_non_string_input(self):
        for bad in (None, 123, ["a", "b"], {"x": 1}):
            with self.assertRaises(TypeError):
                analyze_attack_v19(bad)  # type: ignore[arg-type]

    def test_main_missing_file_exits_cleanly(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["definitely_nonexistent_file_12345.txt"])
        self.assertEqual(2, exit_code)
        self.assertIn("not found", stderr.getvalue())

    def test_main_directory_input_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main([d])
            self.assertEqual(2, exit_code)
            self.assertIn("directory", stderr.getvalue())

    def test_empty_input_is_handled(self):
        result = analyze_attack_v19("")
        self.assertEqual([], result["detections"])
        self.assertEqual("No ATT&CK techniques detected.", result.get("status"))

    def test_rule_and_scope_counts_are_pinned(self):
        from attacks.attack_v19_detector import RULES

        self.assertEqual(22, len(RULES))
        matrices = {r.matrix for r in RULES}
        self.assertEqual({"Enterprise", "Mobile", "ICS"}, matrices)


if __name__ == "__main__":
    unittest.main()
