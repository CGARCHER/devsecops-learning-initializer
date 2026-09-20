"""Comprueba el ciclo de carga, generación y limpieza de proyectos temporales."""

import http.client
import io
import json
import shutil
import tempfile
import threading
import time
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from devsecops_initializer import sessions
from devsecops_initializer.importer import safe_extract_zip
from devsecops_initializer.web import Handler
from test_initializer import POM


def project_zip() -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        # Este nombre no debe confundirse con la carpeta temporal del importador.
        archive.writestr("devsecops-init-example/pom.xml", POM)
    return data.getvalue()


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.session_patch = patch.object(sessions, "SESSIONS", {})
        self.session_patch.start()
        self.addCleanup(self.session_patch.stop)

    def test_extraction_returns_the_complete_workspace(self):
        extracted = safe_extract_zip(project_zip())
        self.addCleanup(shutil.rmtree, extracted.workspace, True)
        self.assertEqual("devsecops-init-example", extracted.root.name)
        self.assertEqual(extracted.workspace / "project" / extracted.root.name, extracted.root)
        self.assertTrue((extracted.root / "pom.xml").is_file())
        self.assertTrue((extracted.workspace / "project.zip").is_file())

    def test_expiration_removes_only_expired_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, current = Path(tmp) / "old", Path(tmp) / "current"
            old.mkdir()
            current.mkdir()
            old_token = sessions.store_session(sessions.UploadSession(old, old, 0, False))
            current_token = sessions.store_session(sessions.UploadSession(current, current, time.time(), False))
            sessions.cleanup_expired_sessions()
            self.assertFalse(old.exists())
            self.assertTrue(current.exists())
            self.assertNotIn(old_token, sessions.SESSIONS)
            self.assertIn(current_token, sessions.SESSIONS)

    def test_session_limit_cleans_rejected_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rejected"
            root.mkdir()
            with patch.object(sessions, "MAX_SESSIONS", 0):
                with self.assertRaisesRegex(ValueError, "ocupado"):
                    sessions.store_session(sessions.UploadSession(root, root, time.time(), False))
            self.assertFalse(root.exists())

    def test_web_generates_zip_once_and_cleans_workspace(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(*server.server_address, timeout=10)
        workspace = None
        try:
            connection.request("POST", "/api/analyze?dashboard=true", project_zip())
            response = connection.getresponse()
            self.assertEqual(200, response.status)
            token = json.loads(response.read())["session"]
            workspace = sessions.SESSIONS[token].workspace
            connection.request("POST", f"/api/generate?session={token}", b"")
            response = connection.getresponse()
            self.assertEqual(200, response.status)
            with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                self.assertIn("compose.security.yml", archive.namelist())
                self.assertIn("pom.xml", archive.namelist())
            self.assertFalse(workspace.exists())
            connection.request("POST", f"/api/generate?session={token}", b"")
            response = connection.getresponse()
            self.assertEqual(400, response.status)
            response.read()
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            if workspace:
                shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
