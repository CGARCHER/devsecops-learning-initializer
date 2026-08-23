from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from devsecops_initializer.dashboard_assets.report_api import local_patch_proposal
from devsecops_initializer.importer import safe_extract_zip
from devsecops_initializer.service import InitializerService
from devsecops_initializer.versioning import DEVSECOPS_VERSION


POM = """<project>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.5.10</version>
  </parent>
  <properties><java.version>17</java.version></properties>
</project>
"""


class InitializerTests(unittest.TestCase):
    def project(self, docker: bool = True) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
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
                ".devsecops/engine/scripts/normalize_findings.py",
                ".devsecops/engine/security/semgrep.yml",
                "docs/devsecops/guia-del-estudiante.md",
                "SECURITY_SETUP.md",
                "pom.xml",
            }
            self.assertTrue(expected.issubset(names))
            ruleset = json.loads(archive.read(".github/rulesets/main-protection.json"))
            checks = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
            self.assertEqual("security / aggregate", checks["parameters"]["required_status_checks"][0]["context"])
            workflow = archive.read(".github/workflows/devsecops.yml").decode()
            self.assertIn(f"Paquete DevSecOps: {DEVSECOPS_VERSION}", workflow)
            self.assertIn(".devsecops/engine/scripts/normalize_findings.py", workflow)
            self.assertNotIn("uses: CGARCHER/devsecops-learning-initializer", workflow)
            manifest = json.loads(archive.read(".devsecops/manifest.json"))
            self.assertEqual(DEVSECOPS_VERSION, manifest["devsecopsVersion"])

    def test_rejects_zip_slip(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("../outside.txt", "bad")
        with self.assertRaisesRegex(ValueError, "ruta no segura"):
            safe_extract_zip(data.getvalue())

    def test_detects_an_available_package_update(self):
        project = self.project()
        manifest = {
            "generatedBy": "devsecops-learning-initializer",
            "devsecopsVersion": "0.9.0",
        }
        (project / ".devsecops").mkdir()
        (project / ".devsecops/manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        version = InitializerService().analyze(project).version

        self.assertIsNotNone(version)
        self.assertEqual("update_available", version.status)
        self.assertEqual("0.9.0", version.installed)

    def test_does_not_downgrade_a_newer_package(self):
        project = self.project()
        (project / ".devsecops").mkdir()
        (project / ".devsecops/manifest.json").write_text(
            json.dumps({"devsecopsVersion": "9.0.0"}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "versión DevSecOps más reciente"):
            InitializerService().generate_zip(project)

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
            guide = archive.read("docs/devsecops/dashboard.md").decode()
            self.assertIn("Actions: Read", guide)
            self.assertIn("La API ya está desplegada", guide)

    def test_recognizes_an_existing_dashboard_directory(self):
        project = self.project()
        (project / ".devsecops/dashboard").mkdir(parents=True)

        plan = InitializerService().analyze(project, include_dashboard=True)

        change = next(item for item in plan.changes if item.path == ".devsecops/dashboard")
        self.assertEqual("modify", change.kind)
        self.assertEqual("Carpeta existente", change.before)

    def test_builds_a_reviewable_patch_without_modifying_the_project(self):
        project = self.project()
        original = (
            "<project>\n"
            "  <dependencies>\n"
            "    <dependency>\n"
            "      <artifactId>log4j-core</artifactId>\n"
            "      <version>2.14.1</version>\n"
            "    </dependency>\n"
            "  </dependencies>\n"
            "</project>\n"
        )
        (project / "pom.xml").write_text(original, encoding="utf-8")
        finding = {
            "id": "CVE-2021-44228",
            "category": "SCA",
            "component": "org.apache.logging.log4j:log4j-core",
            "version": "2.14.1",
            "fixedVersion": "2.17.1",
        }

        result = local_patch_proposal(
            {"patchProposal": {"available": False}},
            finding,
            project,
        )

        patch = result["patchProposal"]
        self.assertTrue(patch["available"])
        self.assertIn("-      <version>2.14.1</version>", patch["content"])
        self.assertIn("+      <version>2.17.1</version>", patch["content"])
        self.assertEqual(original, (project / "pom.xml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
