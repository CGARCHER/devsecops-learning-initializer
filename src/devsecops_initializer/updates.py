"""Limpieza del paquete en la copia temporal, sin vaciar carpetas del proyecto."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from importlib.resources import files
from pathlib import Path


MANAGED_DIRECTORIES = (".devsecops/engine", ".devsecops/dashboard")


def legacy_files(root: Path) -> list[str]:
    """Reconoce las copias antiguas por su contenido, no solo por su nombre.

    El catálogo guarda huellas SHA-256 del prototipo anterior. Así, un script
    propio con el mismo nombre no se confunde con un archivo de la herramienta.
    Se normalizan los saltos de línea para admitir ZIP de Windows y Linux.
    """
    catalog = json.loads(files("devsecops_initializer").joinpath(
        "template_files", "legacy_files.json"
    ).read_text(encoding="utf-8"))
    result = []
    for relative, expected in catalog.items():
        path = root / relative
        if path.is_file():
            content = path.read_bytes().replace(b"\r\n", b"\n")
            if hashlib.sha256(content).hexdigest() == expected:
                result.append(relative)
    return result


def check_legacy_references(root: Path, removed: list[str]) -> None:
    """No entrega un ZIP roto si una integración propia aún usa el paquete antiguo."""
    if not removed:
        return
    references = list(removed)
    for relative in removed:
        if relative.endswith(".py"):
            module = Path(relative).stem
            references.extend((f"from {module} import", f"import {module}"))
    if ".github/workflows/security.yml" in removed:
        references.extend(("security.yml", "Security analysis (asynchronous)"))
    conflicts = []
    # No confunde scripts/x con la ruta nueva .devsecops/engine/scripts/x.
    patterns = [re.compile(r"(?<![\w/.-])(?:\./|\.\./)?" + re.escape(reference)
                           + r"(?![\w.-])") for reference in references]
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if (not path.is_file() or relative in removed
                or any(part in {".git", ".devsecops", "target", "build", "__pycache__"}
                       for part in path.relative_to(root).parts)):
            continue
        if path.suffix not in {".yml", ".yaml", ".py", ".js", ".cjs", ".sh"} and path.name != "Dockerfile":
            continue
        content = path.read_text(encoding="utf-8", errors="replace").replace("\\", "/")
        if any(pattern.search(content) for pattern in patterns):
            conflicts.append(relative)
    if conflicts:
        raise ValueError(
            "Estos archivos todavía utilizan la configuración antigua: "
            + ", ".join(sorted(conflicts))
            + ". Adapta esas referencias al paquete .devsecops antes de actualizar. "
            "El proyecto original no se ha modificado."
        )


def clean_package(workspace: Path, removed: list[str]) -> None:
    """Elimina solo rutas conocidas y comprueba que siguen dentro de la copia."""
    root = workspace.resolve()
    for relative in (*MANAGED_DIRECTORIES, *removed):
        target = root / relative
        if not target.resolve().is_relative_to(root) or target.is_symlink():
            raise ValueError("La carpeta del paquete contiene una ruta no segura.")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
