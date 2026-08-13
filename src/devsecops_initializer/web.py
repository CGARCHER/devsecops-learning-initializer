from __future__ import annotations

import argparse
import json
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .importer import safe_extract_zip
from .service import DEFAULT_WORKFLOW_REPOSITORY, InitializerService


SESSIONS: dict[str, Path] = {}


class Handler(BaseHTTPRequestHandler):
    service = InitializerService()

    def do_GET(self):
        route = urlparse(self.path).path
        asset = "index.html" if route == "/" else route.removeprefix("/")
        if asset not in {"index.html", "app.js", "styles.css"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = files("devsecops_initializer.static").joinpath(asset).read_bytes()
        content_type = {"html": "text/html", "js": "text/javascript", "css": "text/css"}[asset.rsplit(".", 1)[-1]]
        self._send(HTTPStatus.OK, data, content_type + "; charset=utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/analyze":
                length = int(self.headers.get("Content-Length", "0"))
                root = safe_extract_zip(self.rfile.read(length))
                token = secrets.token_urlsafe(18)
                SESSIONS[token] = root
                payload = self.service.analyze(root).public() | {"session": token}
                self._json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/generate":
                query = parse_qs(parsed.query)
                token = query.get("session", [""])[0]
                repository = query.get("repository", [DEFAULT_WORKFLOW_REPOSITORY])[0]
                root = SESSIONS.get(token)
                if not root:
                    raise ValueError("La sesión ha caducado. Vuelve a analizar el ZIP.")
                self._send(HTTPStatus.OK, self.service.generate_zip(root, repository), "application/zip", {"Content-Disposition": 'attachment; filename="proyecto-devsecops.zip"'})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, OSError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _json(self, status: HTTPStatus, payload: dict):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _send(self, status: HTTPStatus, data: bytes, content_type: str, headers: dict[str, str] | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
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

