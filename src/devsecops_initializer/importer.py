from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path


MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_EXPANDED_BYTES = 150 * 1024 * 1024
MAX_ZIP_MEMBERS = 2000


def safe_extract_zip(data: bytes) -> Path:
    """Extrae un ZIP aplicando límites y evitando rutas fuera del directorio temporal."""
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("El ZIP supera el límite de 25 MB.")
    destination = Path(tempfile.mkdtemp(prefix="devsecops-init-"))
    archive_path = destination / "project.zip"
    archive_path.write_bytes(data)
    project_dir = destination / "project"
    project_dir.mkdir()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if len(members) > MAX_ZIP_MEMBERS:
                raise ValueError("El ZIP contiene demasiados archivos.")
            expanded = 0
            paths: set[Path] = set()
            for info in members:
                # Se rechazan elementos que podrían escribir fuera del proyecto o agotar recursos.
                if info.flag_bits & 0x1:
                    raise ValueError("El ZIP contiene archivos cifrados y no puede procesarse.")
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("El ZIP contiene enlaces simbólicos y no puede procesarse.")
                expanded += info.file_size
                if expanded > MAX_EXPANDED_BYTES:
                    raise ValueError("El contenido descomprimido supera el límite permitido.")
                candidate = (project_dir / info.filename).resolve()
                if project_dir.resolve() not in candidate.parents and candidate != project_dir.resolve():
                    raise ValueError("El ZIP contiene una ruta no segura.")
                if not info.is_dir() and candidate in paths:
                    raise ValueError("El ZIP contiene rutas duplicadas.")
                paths.add(candidate)
            archive.extractall(project_dir)
    except zipfile.BadZipFile as error:
        shutil.rmtree(destination, ignore_errors=True)
        raise ValueError("El archivo seleccionado no es un ZIP válido.") from error
    except (ValueError, RuntimeError):
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return normalize_project_root(project_dir)


def normalize_project_root(root: Path) -> Path:
    """Elimina el nivel exterior que suelen añadir las herramientas de compresión."""
    visible = [p for p in root.iterdir() if p.name not in {"__MACOSX", ".DS_Store"}]
    if len(visible) == 1 and visible[0].is_dir():
        return visible[0]
    return root
