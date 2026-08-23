from __future__ import annotations

import argparse
import json
import secrets
import shutil
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlparse

from .importer import MAX_ZIP_BYTES, safe_extract_zip
from .service import InitializerService
from .versioning import DEVSECOPS_VERSION


SESSION_TTL_SECONDS = 30 * 60
MAX_SESSIONS = 20
STATIC_CONTENT_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
}
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; style-src 'self'; script-src 'self'; "
    "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)


@dataclass(frozen=True)
class UploadSession:
    root: Path
    workspace: Path
    created_at: float
    include_dashboard: bool


SESSIONS: dict[str, UploadSession] = {}
SESSIONS_LOCK = Lock()


def upload_workspace(root: Path) -> Path:
    for candidate in (root, *root.parents):
        if candidate.name.startswith("devsecops-init-"):
            return candidate
    raise ValueError("No se ha podido identificar el espacio temporal del proyecto.")


def cleanup_expired_sessions() -> None:
    """Elimina los proyectos temporales cuya sesión ya ha caducado."""
    limit = time.time() - SESSION_TTL_SECONDS
    with SESSIONS_LOCK:
        expired = [token for token, session in SESSIONS.items() if session.created_at < limit]
        sessions = [SESSIONS.pop(token) for token in expired]
    for session in sessions:
        shutil.rmtree(session.workspace, ignore_errors=True)


def store_session(session: UploadSession) -> str:
    """Guarda una sesión temporal y devuelve el identificador para generar el ZIP."""
    with SESSIONS_LOCK:
        if len(SESSIONS) >= MAX_SESSIONS:
            shutil.rmtree(session.workspace, ignore_errors=True)
            raise ValueError("El servicio está ocupado. Inténtalo de nuevo más tarde.")
        token = secrets.token_urlsafe(18)
        SESSIONS[token] = session
    return token


def take_session(token: str) -> UploadSession:
    """Recupera y elimina una sesión para que solo pueda utilizarse una vez."""
    with SESSIONS_LOCK:
        session = SESSIONS.pop(token, None)
    if not session:
        raise ValueError("La sesión ha caducado. Vuelve a analizar el ZIP.")
    return session


class Handler(BaseHTTPRequestHandler):
    service = InitializerService()

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/health":
            self._json(
                HTTPStatus.OK,
                {"status": "UP", "devsecopsVersion": DEVSECOPS_VERSION},
            )
            return

        asset = "index.html" if route == "/" else route.removeprefix("/")
        if asset not in STATIC_CONTENT_TYPES:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        data = files("devsecops_initializer.static").joinpath(asset).read_bytes()
        self._send(HTTPStatus.OK, data, STATIC_CONTENT_TYPES[asset])

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        cleanup_expired_sessions()
        try:
            if parsed.path == "/api/analyze":
                self._analyze_project(parsed.query)
                return
            if parsed.path == "/api/generate":
                self._generate_project(parsed.query)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, OSError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _analyze_project(self, query: str) -> None:
        """Analiza el ZIP y crea la sesión necesaria para generar la copia."""
        options = parse_qs(query)
        include_dashboard = options.get("dashboard", ["false"])[0].lower() == "true"
        root = safe_extract_zip(self._read_upload())
        workspace = upload_workspace(root)

        try:
            plan = self.service.analyze(root, include_dashboard).public()
        except (ValueError, OSError):
            shutil.rmtree(workspace, ignore_errors=True)
            raise

        session = UploadSession(root, workspace, time.time(), include_dashboard)
        token = store_session(session)
        self._json(HTTPStatus.OK, plan | {"session": token})

    def _read_upload(self) -> bytes:
        """Lee el cuerpo de la petición respetando el límite de tamaño."""
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("No se ha recibido ningún ZIP.")
        if length > MAX_ZIP_BYTES:
            raise ValueError("El ZIP supera el límite de 25 MB.")
        return self.rfile.read(length)

    def _generate_project(self, query: str) -> None:
        """Genera el ZIP y elimina los archivos temporales de la sesión."""
        token = parse_qs(query).get("session", [""])[0]
        session = take_session(token)
        try:
            result = self.service.generate_zip(
                session.root,
                session.include_dashboard,
            )
        finally:
            shutil.rmtree(session.workspace, ignore_errors=True)

        self._send(
            HTTPStatus.OK,
            result,
            "application/zip",
            {"Content-Disposition": 'attachment; filename="proyecto-devsecops.zip"'},
        )

    def _json(self, status: HTTPStatus, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self._send(status, data, "application/json; charset=utf-8")

    def _send(
        self,
        status: HTTPStatus,
        data: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args(argv)
    print(f"DevSecOps Learning Initializer: http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
