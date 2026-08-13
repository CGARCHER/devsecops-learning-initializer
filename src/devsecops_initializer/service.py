from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from pathlib import Path

from .models import AnalysisPlan, Change
from .registry import ProfileRegistry
from .templates import WORKFLOW, config_text, manifest, student_guide


DEFAULT_WORKFLOW_REPOSITORY = "CGARCHER/devsecops-learning-initializer"


class InitializerService:
    def __init__(self, registry: ProfileRegistry | None = None):
        self.registry = registry or ProfileRegistry()

    def analyze(self, root: Path) -> AnalysisPlan:
        root = root.resolve()
        profile, confidence = self.registry.resolve(root)
        facts = profile.inspect(root, confidence)
        common = [
            self._change(root, ".github/workflows/devsecops.yml", "Flujo DevSecOps reutilizable", "Ejecuta SAST, SCA y análisis de contenedores por rama."),
            self._change(root, ".devsecops/config.yml", "Configuración normalizada", "Separa la configuración del proyecto de las herramientas concretas."),
            self._change(root, "docs/devsecops/guia-del-estudiante.md", "Guía para el estudiante", "Explica el flujo recomendado y cómo comprobar una corrección."),
            self._change(root, ".devsecops/manifest.json", "Manifiesto de generación", "Registra qué perfil y capacidades se han aplicado."),
        ]
        return AnalysisPlan(facts, common + profile.plan(facts), profile.learning_content(facts))

    @staticmethod
    def _change(root: Path, relative: str, title: str, reason: str) -> Change:
        target = root / relative
        if target.exists():
            before = target.read_text(encoding="utf-8", errors="ignore").splitlines()
            return Change("modify", relative, title, reason, line=1, before=before[0] if before else "(archivo vacío)", after="Contenido regenerado por el asistente")
        return Change("add", relative, title, reason, line=1, after="Archivo nuevo")

    def generate_zip(self, root: Path, repository: str = DEFAULT_WORKFLOW_REPOSITORY) -> bytes:
        plan = self.analyze(root)
        workspace = Path(tempfile.mkdtemp(prefix="devsecops-output-")) / "project"
        shutil.copytree(root, workspace, ignore=shutil.ignore_patterns(".git", "target", "build", "__pycache__"))
        generated = {
            ".github/workflows/devsecops.yml": WORKFLOW.format(repository=repository, profile=plan.facts.profile_id),
            ".devsecops/config.yml": config_text(plan.facts, repository),
            "docs/devsecops/guia-del-estudiante.md": student_guide(plan.facts),
            ".devsecops/manifest.json": manifest(plan.facts),
        }
        for relative, content in generated.items():
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(workspace.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(workspace).as_posix())
        shutil.rmtree(workspace.parent, ignore_errors=True)
        return output.getvalue()

