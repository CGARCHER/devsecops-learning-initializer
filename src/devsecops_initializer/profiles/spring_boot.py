from __future__ import annotations

import re
from pathlib import Path

from ..models import Change, LearningCard, ProjectFacts
from .base import FrameworkProfile


class SpringBootProfile(FrameworkProfile):
    id = "spring-boot"
    name = "Spring Boot"

    def detect(self, root: Path) -> int:
        score = 0
        pom = root / "pom.xml"
        gradle = next((p for p in (root / "build.gradle", root / "build.gradle.kts") if p.exists()), None)
        text = ""
        if pom.exists():
            score += 25
            text = pom.read_text(encoding="utf-8", errors="ignore")
        elif gradle:
            score += 25
            text = gradle.read_text(encoding="utf-8", errors="ignore")
        if "spring-boot" in text.lower() or "org.springframework.boot" in text.lower():
            score += 60
        if (root / "src" / "main" / "java").exists():
            score += 10
        return min(score, 100)

    def inspect(self, root: Path, confidence: int) -> ProjectFacts:
        pom = root / "pom.xml"
        gradle = root / "build.gradle"
        gradle_kts = root / "build.gradle.kts"
        if pom.exists():
            build_system, build_file = "maven", pom
        elif gradle.exists() or gradle_kts.exists():
            build_system, build_file = "gradle", gradle if gradle.exists() else gradle_kts
        else:
            build_system, build_file = "unknown", None
        text = build_file.read_text(encoding="utf-8", errors="ignore") if build_file else ""
        version_patterns = (
            r"<java\.version>\s*([^<]+)",
            r"JavaLanguageVersion\.of\((\d+)\)",
            r"sourceCompatibility\s*=\s*['\"]?(\d+)",
        )
        java_version = "auto"
        for pattern in version_patterns:
            match = re.search(pattern, text)
            if match:
                java_version = match.group(1).strip()
                break
        dockerfile = next((p for p in root.rglob("Dockerfile") if ".git" not in p.parts), None)
        evidence = [build_file.name] if build_file else []
        if dockerfile:
            evidence.append(dockerfile.relative_to(root).as_posix())
        return ProjectFacts(
            profile_id=self.id,
            profile_name=self.name,
            confidence=confidence,
            project_root=root,
            build_system=build_system,
            java_version=java_version,
            dockerfile=dockerfile.relative_to(root).as_posix() if dockerfile else None,
            evidence=tuple(evidence),
        )

    def plan(self, facts: ProjectFacts) -> list[Change]:
        result: list[Change] = []
        if facts.build_system == "unknown":
            result.append(Change(
                "not_applicable", "pom.xml / build.gradle", "SCA de dependencias",
                "No se ha localizado un descriptor Maven o Gradle; el análisis SCA no se activa.",
            ))
        if not facts.dockerfile:
            result.append(Change(
                "not_applicable", "Dockerfile", "Análisis de contenedores",
                "El proyecto no contiene Dockerfile. El flujo lo indicará como no aplicable, no como cero hallazgos.",
            ))
        return result

    def learning_content(self, facts: ProjectFacts) -> list[LearningCard]:
        return [
            LearningCard(
                "SAST: revisar el código antes de ejecutar",
                "Semgrep busca patrones inseguros en el código fuente. Un hallazgo debe revisarse en su contexto; no implica por sí solo que exista una explotación.",
                ("Abrir la ruta y la línea indicadas", "Corregir en una rama feature", "Volver a ejecutar el flujo"),
            ),
            LearningCard(
                "SCA: conocer las dependencias reales",
                f"El flujo genera un SBOM CycloneDX desde {facts.build_system} y Trivy analiza las dependencias directas y transitivas.",
                ("Revisar versión instalada y versión corregida", "Preferir el gestor de versiones de Spring Boot", "Ejecutar pruebas de regresión"),
            ),
            LearningCard(
                "Contenedor: analizar lo que se despliega",
                "Si existe Dockerfile, la imagen se construye y analiza de forma independiente al código y a las dependencias Java.",
                ("Actualizar imágenes base con tags controlados", "Evitar ejecutar como root", "Comprobar de nuevo la imagen final"),
            ),
        ]

