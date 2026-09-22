from __future__ import annotations

import re
from pathlib import Path

from ..models import Change, LearningCard, ProjectFacts
from .base import FrameworkProfile


BUILD_FILES = (
    ("maven", "pom.xml"),
    ("gradle", "build.gradle"),
    ("gradle", "build.gradle.kts"),
)

JAVA_VERSION_PATTERNS = (
    r"<java\.version>\s*([^<]+)",
    r"JavaLanguageVersion\.of\((\d+)\)",
    r"sourceCompatibility\s*=\s*['\"]?(\d+)",
)

# El Dockerfile del panel generado no pertenece a la aplicación Spring Boot.
IGNORED_DIRECTORIES = {".git", ".devsecops", "build", "target"}


class SpringBootProfile(FrameworkProfile):
    id = "spring-boot"
    name = "Spring Boot"

    def detect(self, root: Path) -> int:
        """Calcula la confianza a partir del descriptor y la estructura Java."""
        score = 0
        _, build_file = self._build_descriptor(root)
        if build_file:
            score += 25
            text = self._read(build_file)
        else:
            text = ""

        if "spring-boot" in text.lower() or "org.springframework.boot" in text.lower():
            score += 60
        if (root / "src" / "main" / "java").exists():
            score += 10
        return min(score, 100)

    def inspect(self, root: Path, confidence: int) -> ProjectFacts:
        """Obtiene los datos que utilizarán el workflow y las guías generadas."""
        build_system, build_file = self._build_descriptor(root)
        build_text = self._read(build_file) if build_file else ""
        dockerfile = self._find_dockerfile(root)

        evidence = [build_file.name] if build_file else []
        if dockerfile:
            evidence.append(dockerfile.relative_to(root).as_posix())

        return ProjectFacts(
            profile_id=self.id,
            profile_name=self.name,
            confidence=confidence,
            project_root=root,
            build_system=build_system,
            java_version=self._java_version(build_text),
            dockerfile=dockerfile.relative_to(root).as_posix() if dockerfile else None,
            evidence=tuple(evidence),
        )

    @staticmethod
    def _build_descriptor(root: Path) -> tuple[str, Path | None]:
        """Localiza el primer descriptor Maven o Gradle compatible."""
        for build_system, filename in BUILD_FILES:
            candidate = root / filename
            if candidate.is_file():
                return build_system, candidate
        return "unknown", None

    @staticmethod
    def _read(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _java_version(build_text: str) -> str:
        """Extrae la versión de Java o devuelve auto cuando no está declarada."""
        for pattern in JAVA_VERSION_PATTERNS:
            match = re.search(pattern, build_text)
            if match:
                return match.group(1).strip()
        return "auto"

    @staticmethod
    def _find_dockerfile(root: Path) -> Path | None:
        """Busca el Dockerfile sin entrar en carpetas generadas."""
        return next(
            (
                path
                for path in root.rglob("Dockerfile")
                if not IGNORED_DIRECTORIES.intersection(
                    path.relative_to(root).parts
                )
            ),
            None,
        )

    def plan(self, facts: ProjectFacts) -> list[Change]:
        result: list[Change] = []
        if facts.build_system == "unknown":
            result.append(
                Change(
                    "not_applicable",
                    "pom.xml / build.gradle",
                    "SCA de dependencias",
                    "No se ha localizado un descriptor Maven o Gradle; el análisis SCA no se activa.",
                )
            )
        if not facts.dockerfile:
            result.append(
                Change(
                    "not_applicable",
                    "Dockerfile",
                    "Análisis de contenedores",
                    "El proyecto no contiene Dockerfile. El flujo lo indicará "
                    "como no aplicable, no como cero hallazgos.",
                )
            )
        return result

    def learning_content(self, facts: ProjectFacts) -> list[LearningCard]:
        return [
            LearningCard(
                "SAST: revisar el código antes de ejecutar",
                "Semgrep busca patrones inseguros en el código fuente. Un "
                "hallazgo debe revisarse en su contexto; no implica por sí "
                "solo que exista una explotación.",
                (
                    "Abrir la ruta y la línea indicadas",
                    "Corregir en una rama feature",
                    "Volver a ejecutar el flujo",
                ),
            ),
            LearningCard(
                "SCA: conocer las dependencias reales",
                f"El flujo genera un SBOM CycloneDX desde {facts.build_system} "
                "y Trivy analiza las dependencias directas y transitivas.",
                (
                    "Revisar versión instalada y versión corregida",
                    "Preferir el gestor de versiones de Spring Boot",
                    "Ejecutar pruebas de regresión",
                ),
            ),
            LearningCard(
                "Contenedor: analizar lo que se despliega",
                "Si existe Dockerfile, la imagen se construye y analiza de "
                "forma independiente al código y a las dependencias Java.",
                (
                    "Actualizar imágenes base con tags controlados",
                    "Evitar ejecutar como root",
                    "Comprobar de nuevo la imagen final",
                ),
            ),
        ]
