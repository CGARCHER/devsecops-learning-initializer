"""Actualización de proyectos sin conservar restos ni borrar archivos del alumno."""

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from devsecops_initializer.service import InitializerService
from devsecops_initializer.updates import clean_package, legacy_files
from devsecops_initializer.versioning import DEVSECOPS_VERSION


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        self.write("pom.xml", "<project><parent><groupId>org.springframework.boot</groupId>"
                   "<artifactId>spring-boot-starter-parent</artifactId>"
                   "<version>3.5.10</version></parent></project>")
        self.service = InitializerService()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))

    def archive(self, dashboard=False):
        with zipfile.ZipFile(io.BytesIO(self.service.generate_zip(self.root, dashboard))) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def test_update_replaces_package_and_preserves_project_and_settings(self):
        first = self.archive(dashboard=True)
        for name, content in first.items():
            self.write(name, content.decode())
        self.write(".devsecops/engine/obsolete.py", "obsolete engine")
        self.write(".devsecops/dashboard/static/obsolete.js", "obsolete dashboard")
        self.write(".devsecops/dashboard/static/app.js", "old dashboard")
        preserved = {
            "scripts/deploy_dokploy.cjs": "project deployment",
            "scripts/own.py": "own script",
            "dashboard/own.html": "own dashboard",
            ".devsecops/dashboard.env": "LOCAL_SETTING=keep",
            ".devsecops/.gitignore": "dashboard.env\nmy-local-file\n",
            "reports/report.json": "{}",
            ".github/workflows/ci.yml": "name: My CI",
            "docs/devsecops/my-notes.md": "my notes",
        }
        for name, content in preserved.items():
            self.write(name, content)
        result = self.archive()  # El panel ya instalado no depende de la casilla.
        self.assertNotIn(".devsecops/engine/obsolete.py", result)
        self.assertNotIn(".devsecops/dashboard/static/obsolete.js", result)
        self.assertEqual(first[".devsecops/dashboard/static/app.js"], result[".devsecops/dashboard/static/app.js"])
        for name, content in preserved.items():
            self.assertEqual(content.encode(), result[name])
        self.assertTrue((self.root / ".devsecops/engine/obsolete.py").exists())
        manifest = json.loads(result[".devsecops/manifest.json"])
        self.assertTrue(manifest["capabilities"]["localDashboard"])
        self.assertEqual(DEVSECOPS_VERSION, manifest["devsecopsVersion"])

    def test_updating_twice_produces_the_same_files(self):
        first = self.archive(dashboard=True)
        for name, content in first.items():
            self.write(name, content.decode())
        self.assertEqual(first, self.archive())

    def test_base_only_stays_without_dashboard(self):
        result = self.archive()
        self.assertFalse(any(name.startswith(".devsecops/dashboard") for name in result))
        self.assertFalse(json.loads(result[".devsecops/manifest.json"])["capabilities"]["localDashboard"])

    def test_known_legacy_file_is_removed_but_same_name_custom_file_is_kept(self):
        name = "scripts/evaluate_policy.py"
        original = "# known legacy content\n"
        catalog = json.dumps({name: hashlib.sha256(original.encode()).hexdigest()})
        with patch("devsecops_initializer.updates.files") as resources:
            resources.return_value.joinpath.return_value.read_text.return_value = catalog
            self.write(name, original)
            self.assertEqual([name], legacy_files(self.root))
            plan = self.service.analyze(self.root)
            self.assertTrue(any(change.kind == "delete" and change.path == name for change in plan.changes))
            self.assertNotIn(name, self.archive())
            self.assertTrue((self.root / name).exists())
            self.write(name, "# my custom script")
            self.assertEqual([], legacy_files(self.root))
            self.assertIn(name, self.archive())

    def test_legacy_reference_prevents_a_broken_copy(self):
        name = "scripts/authorize_deployment.cjs"
        self.write(name, "legacy")
        self.write(".github/workflows/deploy.yml", "run: node scripts/authorize_deployment.cjs")
        with patch("devsecops_initializer.service.legacy_files", return_value=[name]):
            with self.assertRaisesRegex(ValueError, "deploy.yml"):
                self.service.generate_zip(self.root)
        self.assertEqual("legacy", (self.root / name).read_text())

    def test_cleanup_rejects_a_path_outside_the_copy(self):
        outside = self.root.parent / "keep.txt"
        outside.write_text("keep")
        with self.assertRaisesRegex(ValueError, "ruta no segura"):
            clean_package(self.root, ["../keep.txt"])
        self.assertEqual("keep", outside.read_text())

    def test_new_reference_does_not_prevent_removing_old_copy(self):
        name = "scripts/authorize_deployment.cjs"
        self.write(name, "legacy")
        self.write(".github/workflows/deploy.yml", "run: node .devsecops/engine/scripts/authorize_deployment.cjs")
        with patch("devsecops_initializer.service.legacy_files", return_value=[name]):
            self.assertNotIn(name, self.archive())


if __name__ == "__main__":
    unittest.main()
