from __future__ import annotations

import json

from .models import ProjectFacts


WORKFLOW = """name: Seguridad DevSecOps

on:
  push:
    branches: [develop, main, 'feature/**']
  pull_request:
  workflow_dispatch:

jobs:
  security:
    uses: {repository}/.github/workflows/security-reusable.yml@main
    with:
      project_path: auto
      dockerfile: auto
      engine_repository: '{repository}'
      engine_ref: main
    secrets: inherit
"""


def config_text(facts: ProjectFacts, repository: str) -> str:
    dockerfile = facts.dockerfile or "auto"
    return f"""schemaVersion: '1.0'
profile:
  id: {facts.profile_id}
project:
  root: .
  buildSystem: {facts.build_system}
  javaVersion: {facts.java_version}
  dockerfile: {dockerfile}
analysis:
  sast: semgrep
  sca: trivy-sca
  container: trivy
policy:
  blockOn: [CRITICAL]
  requireReviewOn: [HIGH]
workflowRepository: {repository}
"""


def student_guide(facts: ProjectFacts) -> str:
    container = "se construye y analiza la imagen" if facts.dockerfile else "se registra como no aplicable porque no hay Dockerfile"
    return f"""# Guía DevSecOps del proyecto

## Qué se ha detectado

- Perfil: {facts.profile_name}
- Construcción: {facts.build_system}
- Java: {facts.java_version}
- Contenedores: {container}

## Flujo de trabajo recomendado

1. Trabaja en una rama `feature/*` y sube cambios pequeños.
2. Revisa SAST, SCA y contenedores como controles distintos.
3. Corrige primero los hallazgos críticos y confirma la solución con una nueva ejecución.
4. Integra en `develop` cuando el informe sea válido y la política esté aprobada.
5. Promueve a `main` y producción únicamente el mismo commit que ha superado los controles.

## Cómo leer el informe

Un hallazgo incluye tecnología, herramienta, severidad, componente o regla y ubicación. Si una remediación modifica `pom.xml` o `Dockerfile`, debe mostrar la línea localizada, el contenido eliminado y el contenido añadido. “No aplicable” no significa “cero vulnerabilidades”: significa que ese control no corresponde al proyecto detectado.

## Comprobación

Abre la ejecución de GitHub Actions, descarga el artefacto `devsecops-security-report-*` y confirma que los resultados pertenecen al SHA analizado. Después de una corrección, vuelve a ejecutar el análisis; no cierres un hallazgo solo porque el código haya cambiado.
"""


def manifest(facts: ProjectFacts) -> str:
    return json.dumps({"schemaVersion": "1.0", "generatedBy": "devsecops-learning-initializer", "profile": facts.public()}, ensure_ascii=False, indent=2)
