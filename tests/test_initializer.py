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
from devsecops_initializer.web import static_asset


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
                ".github/workflows/authorize-main.yml",
                ".github/rulesets/main-protection.json",
                ".github/rulesets/develop-protection.json",
                ".devsecops/engine/scripts/normalize_findings.py",
                ".devsecops/engine/scripts/authorize_deployment.cjs",
                ".devsecops/engine/security/semgrep.yml",
                "docs/devsecops/guia-del-estudiante.md",
                "SECURITY_SETUP.md",
                "pom.xml",
            }
            self.assertTrue(expected.issubset(names))
            ruleset = json.loads(archive.read(".github/rulesets/main-protection.json"))
            checks = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
            self.assertEqual("security / aggregate", checks["parameters"]["required_status_checks"][0]["context"])
            self.assertEqual(["refs/heads/main"], ruleset["conditions"]["ref_name"]["include"])
            review = next(rule["parameters"] for rule in ruleset["rules"] if rule["type"] == "pull_request")
            self.assertEqual(0, review["required_approving_review_count"])
            self.assertTrue(review["dismiss_stale_reviews_on_push"])
            authorization = archive.read(".github/workflows/authorize-main.yml").decode()
            self.assertIn("workflow_call:", authorization)
            self.assertIn("workflow_id: 'devsecops.yml'", authorization)
            self.assertIn("devsecops-security-report-${{ env.DEPLOY_SHA }}", authorization)
            self.assertIn("jobs.authorize.outputs.allowed", authorization)
            self.assertIn("jobs.authorize.outputs.sha", authorization)
            self.assertNotIn("DOKPLOY", authorization)
            workflow = archive.read(".github/workflows/devsecops.yml").decode()
            self.assertIn(f"Paquete DevSecOps: {DEVSECOPS_VERSION}", workflow)
            self.assertIn(".devsecops/engine/scripts/normalize_findings.py", workflow)
            self.assertIn("Motivo del análisis de contenedor", workflow)
            self.assertIn('cron: "0 6 * * 1"', workflow)
            self.assertNotIn("uses: CGARCHER/devsecops-learning-initializer", workflow)
            manifest = json.loads(archive.read(".devsecops/manifest.json"))
            self.assertEqual(DEVSECOPS_VERSION, manifest["devsecopsVersion"])

    def test_shows_current_version_in_initializer_footer(self):
        html = static_asset("index.html").decode()
        self.assertIn(f"v{DEVSECOPS_VERSION}", html)
        self.assertNotIn("__DEVSECOPS_VERSION__", html)

    def test_initializer_frontend_is_clear_for_students(self):
        html = static_asset("index.html").decode()
        script = static_asset("app.js").decode()

        self.assertNotIn("Hardening local", html)
        self.assertNotIn("hardening:", script)
        self.assertIn("Ejecutar automáticamente los análisis de seguridad", html)
        self.assertIn("promocionarse a producción", html)
        self.assertIn("Si marcas esta opción", html)
        self.assertIn("Archivo o componente relacionado", html)
        self.assertIn("Maven o Gradle", script)
        self.assertIn("No deben incluirse credenciales", script)

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
            "devsecopsVersion": "0.8.0",
        }
        (project / ".devsecops").mkdir()
        (project / ".devsecops/manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        version = InitializerService().analyze(project).version

        self.assertIsNotNone(version)
        self.assertEqual("update_available", version.status)
        self.assertEqual("0.8.0", version.installed)

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
                "docs/devsecops/dashboard.md",
            }
            self.assertTrue(expected.issubset(names))
            dashboard = archive.read(".devsecops/dashboard/static/index.html").decode()
            self.assertIn(f"v{DEVSECOPS_VERSION}", dashboard)
            self.assertNotIn("__DEVSECOPS_VERSION__", dashboard)
            environment = archive.read(".devsecops/dashboard.env.example").decode()
            self.assertIn("GH_TOKEN=", environment)
            self.assertIn("AI_API_TOKEN=", environment)
            compose = archive.read("compose.security.yml").decode()
            self.assertIn("DASHBOARD_CONFIG_FILE", compose)
            self.assertIn("127.0.0.1:8081:8080", compose)
            self.assertIn('<option value="UNKNOWN">UNKNOWN</option>', dashboard)
            self.assertNotIn("env_file:", compose)
            self.assertNotIn(".devsecops/secrets", compose)
            report_script = archive.read(".devsecops/dashboard/security_report.sh").decode()
            self.assertIn('gh api --method GET "repos/$repository/actions/runs"', report_script)
            self.assertIn('select(.path == $workflow_path)', report_script)
            self.assertNotIn("gh run list", report_script)
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
