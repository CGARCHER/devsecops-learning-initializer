from __future__ import annotations

import io
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

    def test_generates_copy_with_workflow_and_guide(self):
        result = InitializerService().generate_zip(self.project())
        with zipfile.ZipFile(io.BytesIO(result)) as archive:
            names = set(archive.namelist())
            self.assertIn(".github/workflows/devsecops.yml", names)
            self.assertIn("docs/devsecops/guia-del-estudiante.md", names)
            self.assertIn("pom.xml", names)

    def test_rejects_zip_slip(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("../outside.txt", "bad")
        with self.assertRaisesRegex(ValueError, "ruta no segura"):
            safe_extract_zip(data.getvalue())


if __name__ == "__main__":
    unittest.main()
