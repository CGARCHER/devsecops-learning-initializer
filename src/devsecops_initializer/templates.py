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


def ruleset_text(branch: str) -> str:
    """Crea el ruleset mínimo para proteger main o develop."""
    include = ["~DEFAULT_BRANCH"] if branch == "main" else ["refs/heads/develop"]
    ruleset = {
        "name": f"Protección de {branch} con DevSecOps",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": include, "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {
                "type": "pull_request",
                "parameters": {
                    "allowed_merge_methods": ["merge", "squash", "rebase"],
                    "dismiss_stale_reviews_on_push": False,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 0,
                    "required_review_thread_resolution": False,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "do_not_enforce_on_create": False,
                    "required_status_checks": [{"context": "security / aggregate"}],
                    "strict_required_status_checks_policy": False,
                },
            },
        ],
    }
    return json.dumps(ruleset, ensure_ascii=False, indent=2) + "\n"


def security_setup() -> str:
    return """# Configuración de seguridad en GitHub

El proyecto incluye dos rulesets para proteger las ramas `develop` y `main`. La importación es manual y no requiere entregar un token con permisos administrativos.

## 1. Publicar la configuración

Sube los archivos generados a GitHub. Si la rama `develop` todavía no existe, créala desde `main`.

## 2. Ejecutar el workflow

Abre la pestaña **Actions** y comprueba que el workflow `Seguridad DevSecOps` termina correctamente. Esta primera ejecución registra el check `security / aggregate` que utilizarán los rulesets.

## 3. Importar los rulesets

Accede a `Settings → Rules → Rulesets`, selecciona **New ruleset** y después **Import a ruleset**. Importa por separado:

- `.github/rulesets/develop-protection.json`
- `.github/rulesets/main-protection.json`

Antes de guardar, comprueba que cada ruleset protege la rama indicada.

## 4. Comprobar la protección

Crea una rama `feature/*` y abre una pull request hacia `develop`. GitHub debe exigir el check `security / aggregate` antes de permitir la integración. Después, la promoción a `main` se realiza mediante otra pull request.

Los rulesets impiden eliminar las ramas protegidas, evitan actualizaciones que no sean de avance rápido y obligan a utilizar pull requests con el análisis de seguridad superado.
"""


def config_text(facts: ProjectFacts, repository: str, include_dashboard: bool = False) -> str:
    """Genera la configuración común que utilizará el workflow reutilizable."""
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
dashboard:
  enabled: {str(include_dashboard).lower()}
"""


def dashboard_compose() -> str:
    return """services:
  security-dashboard:
    build:
      context: ./.devsecops/dashboard
    image: devsecops-learning-dashboard:local
    ports:
      - "8081:8080"
    env_file:
      - ./.devsecops/dashboard.env
    environment:
      REPORT_ROOT: /workspace/reports
      SOURCE_ROOT: /workspace/source
      GH_TOKEN_FILE: /run/secrets/github_token
      AI_REMEDIATION_ENABLED: "true"
      AI_API_TOKEN_FILE: /run/secrets/ai_api_token
    secrets:
      # Los tokens se leen desde archivos locales y no se incluyen en la imagen.
      - github_token
      - ai_api_token
    volumes:
      - security-reports:/workspace/reports
      # El panel puede leer el código para orientar el parche, pero no modificarlo.
      - ./:/workspace/source:ro
    read_only: true
    tmpfs:
      - /tmp:size=32m,noexec,nosuid
    cap_drop: [ALL]
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O - http://127.0.0.1:8080/health >/dev/null || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  security-reports:

secrets:
  github_token:
    file: ./.devsecops/secrets/github_token.txt
  ai_api_token:
    file: ./.devsecops/secrets/ai_api_token.txt
"""


def dashboard_environment() -> str:
    return """GITHUB_REPOSITORY=propietario/repositorio
GITHUB_WORKFLOW_FILE=devsecops.yml
GITHUB_BRANCH=develop
AI_API_URL=https://ai-api.cgarcher.dev/api/v1/remediations
"""


def dashboard_guide() -> str:
    return """# Panel local de seguridad

El panel descarga el último informe de GitHub Actions y permite solicitar una explicación educativa a la API de IA. Solo se ejecuta en el equipo del alumno.

## 1. Configurar el repositorio

Copia `.devsecops/dashboard.env.example` como `.devsecops/dashboard.env` y sustituye `propietario/repositorio` por el repositorio real.

## 2. Configurar el acceso a GitHub

Crea un token *fine-grained*, limítalo al repositorio y concede los permisos **Actions: Read** y **Contents: Read**. Guarda únicamente el token en:

`.devsecops/secrets/github_token.txt`

## 3. Configurar el acceso a la IA

La API ya está desplegada y no requiere instalar ni configurar modelos. Guarda el Bearer Token facilitado en:

`.devsecops/secrets/ai_api_token.txt`

No añadas ninguno de estos archivos a Git.

## 4. Arrancar el panel

```bash
docker compose -f compose.security.yml up -d --build
```

Abre `http://localhost:8081` y pulsa **Buscar último informe**.

El código fuente se monta en modo de solo lectura. La IA devuelve una propuesta orientativa, pero el panel no modifica ningún fichero del proyecto.
"""


def devsecops_gitignore() -> str:
    return """dashboard.env
secrets/*
!secrets/.gitignore
"""


def secrets_gitignore() -> str:
    return """*
!.gitignore
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


def manifest(facts: ProjectFacts, include_dashboard: bool = False) -> str:
    """Registra el perfil detectado y las capacidades incluidas en el ZIP."""
    return json.dumps({
        "schemaVersion": "1.0",
        "generatedBy": "devsecops-learning-initializer",
        "profile": facts.public(),
        "capabilities": {"securityPipeline": True, "localDashboard": include_dashboard},
    }, ensure_ascii=False, indent=2)
