"""Sesiones temporales de las cargas ZIP y limpieza de los proyectos caducados."""

from __future__ import annotations

import secrets
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

SESSION_TTL_SECONDS = 30 * 60
MAX_SESSIONS = 20


@dataclass(frozen=True)
class UploadSession:
    root: Path
    workspace: Path
    created_at: float
    include_dashboard: bool


SESSIONS: dict[str, UploadSession] = {}
SESSIONS_LOCK = Lock()


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
