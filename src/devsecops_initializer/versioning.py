from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


DEVSECOPS_VERSION = "0.9.4"
VersionState = Literal["not_installed", "current", "update_available", "newer"]


@dataclass(frozen=True)
class VersionStatus:
    """Describe la versión DevSecOps encontrada en el proyecto."""

    current: str
    installed: str | None
    status: VersionState

    def public(self) -> dict[str, str | None]:
        return {
            "current": self.current,
            "installed": self.installed,
            "status": self.status,
        }


def inspect_version(root: Path) -> VersionStatus:
    """Compara el manifiesto existente con la versión del inicializador."""
    manifest_path = root / ".devsecops/manifest.json"
    if not manifest_path.is_file():
        return VersionStatus(DEVSECOPS_VERSION, None, "not_installed")

    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return VersionStatus(DEVSECOPS_VERSION, "sin versión", "update_available")

    installed = document.get("devsecopsVersion")
    if not isinstance(installed, str) or not _version_tuple(installed):
        return VersionStatus(DEVSECOPS_VERSION, "sin versión", "update_available")

    installed_tuple = _version_tuple(installed)
    current_tuple = _version_tuple(DEVSECOPS_VERSION)
    assert installed_tuple is not None and current_tuple is not None
    if installed_tuple == current_tuple:
        state: VersionState = "current"
    elif installed_tuple < current_tuple:
        state = "update_available"
    else:
        state = "newer"
    return VersionStatus(DEVSECOPS_VERSION, installed, state)


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    return tuple(map(int, match.groups())) if match else None
