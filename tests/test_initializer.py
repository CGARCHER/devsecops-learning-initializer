from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from devsecops_initializer.importer import safe_extract_zip
from devsecops_initializer.service import InitializerService


POM = """<project><parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>3.5.10</version></parent><properties><java.version>17</java.version></properties></project>"""


class InitializerTests(unittest.TestCase):
    def project(self, docker: bool = True) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "pom.xml").write_text(POM, encoding="utf-8")
        (root / "src/main/java").mkdir(parents=True)
        if docker:
            (root / "Dockerfile").write_text("FROM eclipse-temurin:17-jre-alpine\n", encoding="utf-8")
        return root

    def test_detects_spring_boot_maven(self):
        plan = InitializerService().analyze(self.project())
        self.assertEqual("spring-boot", plan.facts.profile_id)
        self.assertEqual("maven", plan.facts.build_system)
        self.assertEqual("17", plan.facts.java_version)
        self.assertTrue(all(change.kind == "add" for change in plan.changes))

    def test_marks_container_not_applicable(self):
        plan = InitializerService().analyze(self.project(docker=False))
        item = next(change for change in plan.changes if change.path == "Dockerfile")
        self.assertEqual("not_applicable", item.kind)

    def test_generates_copy_with_workflow_rulesets_and_guides(self):
        result = InitializerService().generate_zip(self.project())
        with zipfile.ZipFile(io.BytesIO(result)) as archive:
            names = set(archive.namelist())
            expected = {
                ".github/workflows/devsecops.yml",
                ".github/rulesets/main-protection.json",
                ".github/rulesets/develop-protection.json",
                "docs/devsecops/guia-del-estudiante.md",
                "SECURITY_SETUP.md",
                "pom.xml",
            }
            self.assertTrue(expected.issubset(names))
            ruleset = json.loads(archive.read(".github/rulesets/main-protection.json"))
            checks = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
            self.assertEqual("security / aggregate", checks["parameters"]["required_status_checks"][0]["context"])

    def test_rejects_zip_slip(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("../outside.txt", "bad")
        with self.assertRaisesRegex(ValueError, "ruta no segura"):
            safe_extract_zip(data.getvalue())

    def test_rejects_invalid_workflow_repository(self):
        with self.assertRaisesRegex(ValueError, "propietario/repositorio"):
            InitializerService().generate_zip(self.project(), "invalid\nworkflow: injected")

    def test_generates_optional_local_dashboard(self):
        result = InitializerService().generate_zip(self.project(), include_dashboard=True)
        with zipfile.ZipFile(io.BytesIO(result)) as archive:
            names = set(archive.namelist())
            expected = {
                "compose.security.yml",
                ".devsecops/dashboard.env.example",
                ".devsecops/dashboard/Dockerfile",
                ".devsecops/dashboard/report_api.py",
                ".devsecops/dashboard/static/index.html",
                ".devsecops/secrets/.gitignore",
                "docs/devsecops/dashboard.md",
            }
            self.assertTrue(expected.issubset(names))
            manifest = json.loads(archive.read(".devsecops/manifest.json"))
            self.assertTrue(manifest["capabilities"]["localDashboard"])


if __name__ == "__main__":
    unittest.main()
