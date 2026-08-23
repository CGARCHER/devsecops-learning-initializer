from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path

from .models import AnalysisPlan, Change
from .registry import ProfileRegistry
from .templates import (
    config_text,
    dashboard_compose,
    dashboard_environment,
    dashboard_guide,
    devsecops_gitignore,
    manifest,
    ruleset_text,
    secrets_gitignore,
    security_setup,
    student_guide,
)
from .versioning import DEVSECOPS_VERSION, inspect_version


ENGINE_DIRECTORIES = ("profiles", "scripts", "security")

# path, título y explicación que verá el alumno antes de generar el ZIP.
COMMON_PLAN_ITEMS = (
    (
        ".github/workflows/devsecops.yml",
        "Workflow DevSecOps autónomo",
        "Ejecuta SAST, SCA y análisis de contenedores sin depender de otro repositorio.",
    ),
    (
        ".devsecops/engine",
        "Núcleo de análisis",
        "Incluye los perfiles, reglas y scripts utilizados por el workflow.",
    ),
    (
        ".github/rulesets/main-protection.json",
        "Protección de la rama main",
        "Exige una pull request y el resultado favorable del análisis de seguridad.",
    ),
    (
        ".github/rulesets/develop-protection.json",
        "Protección de la rama develop",
        "Aplica el mismo control antes de integrar los cambios de desarrollo.",
    ),
    (
        ".devsecops/config.yml",
        "Configuración normalizada",
        "Separa la configuración del proyecto de las herramientas concretas.",
    ),
    (
        "docs/devsecops/guia-del-estudiante.md",
        "Guía para el estudiante",
        "Explica el flujo recomendado y cómo comprobar una corrección.",
    ),
    (
        "SECURITY_SETUP.md",
        "Configuración de GitHub",
        "Explica cómo importar manualmente los rulesets sin utilizar un token administrativo.",
    ),
    (
        ".devsecops/manifest.json",
        "Manifiesto de generación",
        "Registra qué perfil y capacidades se han aplicado.",
    ),
)

DASHBOARD_PLAN_ITEMS = (
    (
        "compose.security.yml",
        "Panel local de seguridad",
        "Permite consultar los informes y solicitar orientación a la IA.",
    ),
    (
        ".devsecops/dashboard",
        "Aplicación del panel",
        "Incluye los ficheros necesarios para construir el contenedor local.",
    ),
    (
        ".devsecops/dashboard.env.example",
        "Variables del panel",
        "Documenta el repositorio y la rama que se analizarán.",
    ),
    (
        ".devsecops/secrets",
        "Secretos locales",
        "Prepara una carpeta excluida de Git para los tokens.",
    ),
    (
        "docs/devsecops/dashboard.md",
        "Guía del panel",
        "Explica cómo configurar y arrancar el panel local.",
    ),
)

IGNORED_PROJECT_ITEMS = (".git", "target", "build", "__pycache__")


class InitializerService:
    def __init__(self, registry: ProfileRegistry | None = None):
        self.registry = registry or ProfileRegistry()

    def analyze(self, root: Path, include_dashboard: bool = False) -> AnalysisPlan:
        """Detecta el perfil y prepara el listado de cambios sin modificar el proyecto."""
        root = root.resolve()
        profile, confidence = self.registry.resolve(root)
        facts = profile.inspect(root, confidence)

        changes = self._changes_for(root, COMMON_PLAN_ITEMS)
        if include_dashboard:
            changes.extend(self._changes_for(root, DASHBOARD_PLAN_ITEMS))

        changes.extend(profile.plan(facts))
        return AnalysisPlan(
            facts,
            changes,
            profile.learning_content(facts),
            inspect_version(root),
        )

    @classmethod
    def _changes_for(
        cls,
        root: Path,
        items: tuple[tuple[str, str, str], ...],
    ) -> list[Change]:
        """Convierte la descripción de los archivos en cambios visibles para el alumno."""
        return [cls._change(root, path, title, reason) for path, title, reason in items]

    @staticmethod
    def _change(root: Path, relative: str, title: str, reason: str) -> Change:
        target = root / relative
        if target.exists():
            if target.is_dir():
                before = "Carpeta existente"
            else:
                lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
                before = lines[0] if lines else "(archivo vacío)"
            return Change(
                "modify",
                relative,
                title,
                reason,
                line=1,
                before=before,
                after="Contenido regenerado por el asistente",
            )
        return Change("add", relative, title, reason, line=1, after="Archivo nuevo")

    def generate_zip(self, root: Path, include_dashboard: bool = False) -> bytes:
        """Genera una copia ZIP y mantiene intacto el proyecto original."""
        plan = self.analyze(root, include_dashboard)
        if plan.version and plan.version.status == "newer":
            raise ValueError(
                "El proyecto utiliza una versión DevSecOps más reciente que este inicializador."
            )
        temporary = Path(tempfile.mkdtemp(prefix="devsecops-output-"))
        workspace = temporary / "project"
        try:
            # Se trabaja sobre una copia temporal para no sobrescribir archivos del alumno.
            shutil.copytree(root, workspace, ignore=shutil.ignore_patterns(*IGNORED_PROJECT_ITEMS))
            generated = self._generated_files(plan, include_dashboard)
            generated.update(self._engine_files())
            if include_dashboard:
                generated.update(self._dashboard_files())
            self._write_files(workspace, generated)
            return self._compress(workspace)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)

    @classmethod
    def _generated_files(
        cls,
        plan: AnalysisPlan,
        include_dashboard: bool,
    ) -> dict[str, str]:
        """Genera el contenido común a cualquier proyecto compatible."""
        facts = plan.facts
        return {
            ".github/workflows/devsecops.yml": cls._workflow_text(),
            ".github/rulesets/main-protection.json": ruleset_text("main"),
            ".github/rulesets/develop-protection.json": ruleset_text("develop"),
            ".devsecops/config.yml": config_text(facts, include_dashboard),
            "docs/devsecops/guia-del-estudiante.md": student_guide(facts),
            "SECURITY_SETUP.md": security_setup(),
            ".devsecops/manifest.json": manifest(facts, include_dashboard),
        }

    @staticmethod
    def _engine_source() -> Path:
        """Localiza el núcleo tanto en desarrollo como dentro del contenedor."""
        configured = os.getenv("DEVSECOPS_ENGINE_DIR")
        candidates = [
            Path(configured) if configured else None,
            Path(__file__).resolve().parents[2] / "engine",
            Path.cwd() / "engine",
        ]
        for candidate in candidates:
            if candidate and candidate.is_dir():
                return candidate
        raise OSError("No se ha encontrado el núcleo DevSecOps del inicializador.")

    @classmethod
    def _workflow_text(cls) -> str:
        """Carga el workflow autónomo y fija la versión incorporada."""
        template = cls._engine_source() / "workflows/devsecops.yml"
        return template.read_text(encoding="utf-8").replace(
            "__DEVSECOPS_VERSION__",
            DEVSECOPS_VERSION,
        )

    @classmethod
    def _engine_files(cls) -> dict[str, str]:
        """Copia al proyecto únicamente el núcleo que utiliza el workflow."""
        source = cls._engine_source()
        generated: dict[str, str] = {}
        for directory in ENGINE_DIRECTORIES:
            for path in sorted((source / directory).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    relative = path.relative_to(source).as_posix()
                    generated[f".devsecops/engine/{relative}"] = path.read_text(
                        encoding="utf-8"
                    )
        return generated

    @staticmethod
    def _write_files(workspace: Path, generated: dict[str, str]) -> None:
        """Escribe los archivos generados dentro de la copia temporal."""
        for relative, content in generated.items():
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    @staticmethod
    def _compress(workspace: Path) -> bytes:
        """Comprime la copia preparada y devuelve el ZIP en memoria."""
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(workspace.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(workspace).as_posix())
        return output.getvalue()

    @staticmethod
    def _dashboard_files() -> dict[str, str]:
        """Devuelve los archivos del panel que se incluirán en el proyecto generado."""
        assets = files("devsecops_initializer.dashboard_assets")
        generated = {
            "compose.security.yml": dashboard_compose(),
            ".devsecops/dashboard.env.example": dashboard_environment(),
            ".devsecops/.gitignore": devsecops_gitignore(),
            ".devsecops/secrets/.gitignore": secrets_gitignore(),
            "docs/devsecops/dashboard.md": dashboard_guide(),
        }
        for relative in (
            "Dockerfile",
            "report_api.py",
            "security_report.sh",
            "static/index.html",
            "static/app.js",
            "static/styles.css",
        ):
            generated[f".devsecops/dashboard/{relative}"] = assets.joinpath(
                relative
            ).read_text(encoding="utf-8")
        return generated
