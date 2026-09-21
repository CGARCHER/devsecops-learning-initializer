"""Ejecuta la comprobación real del workflow con informes temporales."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / "engine/workflows/devsecops.yml"
GATE = textwrap.dedent(WORKFLOW.read_text(encoding="utf-8").rsplit("python - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])


class AnalysisGateTests(unittest.TestCase):
    def run_gate(self, status="APPROVED", failed_job=None, missing=None):
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory) / "reports/normalized"
            reports.mkdir(parents=True)
            for name, data in {
                "analyzer-status.json": {"status": "SUCCESS", "errors": []},
                "decision.json": {"status": status},
            }.items():
                if name != missing:
                    (reports / name).write_text(json.dumps(data), encoding="utf-8")
            environment = dict(os.environ)
            for job in ("SAST", "SCA", "CONTAINER"):
                environment[f"{job}_RESULT"] = "failure" if job == failed_job else "success"
            return subprocess.run([sys.executable, "-c", GATE], cwd=directory,
                                  env=environment, capture_output=True, text=True)

    def test_findings_allow_review_without_hiding_the_warning(self):
        for status in ("APPROVED", "BLOCKED", "REVIEW_REQUIRED"):
            with self.subTest(status=status):
                result = self.run_gate(status)
                self.assertEqual(0, result.returncode, result.stderr)
                if status != "APPROVED":
                    self.assertIn("::warning", result.stdout)

    def test_technical_errors_remain_blocking(self):
        for options in ({"status": "ANALYSIS_ERROR"}, {"status": "UNKNOWN"},
                        {"failed_job": "SCA"}, {"missing": "decision.json"},
                        {"missing": "analyzer-status.json"}):
            with self.subTest(options=options):
                result = self.run_gate(**options)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("::error", result.stdout)
