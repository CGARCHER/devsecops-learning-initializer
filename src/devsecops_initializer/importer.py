from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path


MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_EXPANDED_BYTES = 150 * 1024 * 1024


def safe_extract_zip(data: bytes) -> Path:
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("El ZIP supera el límite de 25 MB.")
    destination = Path(tempfile.mkdtemp(prefix="devsecops-init-"))
    archive_path = destination / "project.zip"
    archive_path.write_bytes(data)
    project_dir = destination / "project"
    project_dir.mkdir()
    expanded = 0
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            expanded += info.file_size
            if expanded > MAX_EXPANDED_BYTES:
                shutil.rmtree(destination, ignore_errors=True)
                raise ValueError("El contenido descomprimido supera el límite permitido.")
            candidate = (project_dir / info.filename).resolve()
            if project_dir.resolve() not in candidate.parents and candidate != project_dir.resolve():
                shutil.rmtree(destination, ignore_errors=True)
                raise ValueError("El ZIP contiene una ruta no segura.")
        archive.extractall(project_dir)
    return normalize_project_root(project_dir)


def normalize_project_root(root: Path) -> Path:
    visible = [p for p in root.iterdir() if p.name not in {"__MACOSX", ".DS_Store"}]
    if len(visible) == 1 and visible[0].is_dir():
        return visible[0]
    return root

