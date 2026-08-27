from __future__ import annotations

import json
from datetime import date

from .models import ProjectFacts
from .versioning import DEVSECOPS_VERSION


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

El workflow y su núcleo se encuentran dentro del propio proyecto. GitHub Actions no necesita un token personal ni acceder al repositorio del inicializador.

## 3. Importar los rulesets

Accede a `Settings → Rules → Rulesets`, selecciona **New ruleset** y después **Import a ruleset**. Importa por separado:

- `.github/rulesets/develop-protection.json`
- `.github/rulesets/main-protection.json`

Antes de guardar, comprueba que cada ruleset protege la rama indicada.

## 4. Comprobar la protección

Crea una rama `feature/*` y abre una pull request hacia `develop`. GitHub debe exigir el check `security / aggregate` antes de permitir la integración. Después, la promoción a `main` se realiza mediante otra pull request.

Los rulesets impiden eliminar las ramas protegidas, evitan actualizaciones que no sean de avance rápido y obligan a utilizar pull requests con el análisis de seguridad superado.
"""


def config_text(facts: ProjectFacts, include_dashboard: bool = False) -> str:
    """Genera la configuración común del paquete DevSecOps autónomo."""
    dockerfile = facts.dockerfile or "auto"
    return f"""schemaVersion: '1.0'
devsecopsVersion: {DEVSECOPS_VERSION}
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
    environment:
      REPORT_ROOT: /workspace/reports
      SOURCE_ROOT: /workspace/source
      DASHBOARD_CONFIG_FILE: /run/secrets/dashboard.env
      AI_REMEDIATION_ENABLED: "true"
    volumes:
      - security-reports:/workspace/reports
      # La configuración se lee como fichero y los tokens no aparecen en docker inspect.
      - ./.devsecops/dashboard.env:/run/secrets/dashboard.env:ro
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
"""


def dashboard_environment() -> str:
    return """# Repositorio y workflow que consultará el panel.
GITHUB_REPOSITORY=propietario/repositorio
GITHUB_WORKFLOW_FILE=devsecops.yml
GITHUB_BRANCH=develop

# API de remediación ya desplegada.
AI_API_URL=https://ai-api.cgarcher.dev/api/v1/remediations

# Credenciales locales. No subas este fichero a Git.
GH_TOKEN=
AI_API_TOKEN=
"""


def dashboard_guide() -> str:
    return """# Panel local de seguridad

El panel descarga el último informe de GitHub Actions y permite solicitar una explicación educativa a la API de IA. Solo se ejecuta en el equipo del alumno.

## 1. Crear la configuración local

Copia el fichero de ejemplo:

```bash
cp .devsecops/dashboard.env.example .devsecops/dashboard.env
```

En Windows PowerShell utiliza `Copy-Item ./.devsecops/dashboard.env.example ./.devsecops/dashboard.env`.

## 2. Completar el único fichero de configuración

Edita `.devsecops/dashboard.env` e indica:

- El repositorio con el formato `propietario/repositorio`.
- Un token *fine-grained* de GitHub limitado al repositorio, con **Actions: Read** y **Contents: Read**.
- El Bearer Token de la API de IA facilitado para el proyecto.

La API ya está desplegada y su URL, el workflow y la rama aparecen configurados. El fichero real está excluido de Git y no debe publicarse.

## 3. Arrancar el panel

```bash
docker compose -f compose.security.yml up -d --build
```

Abre `http://localhost:8081` y pulsa **Buscar último informe**.

Docker monta la configuración como un fichero de solo lectura. Los tokens no se incluyen en la imagen ni aparecen en `docker inspect`. El código fuente también se monta en modo de solo lectura y el panel no modifica ningún fichero del proyecto.
"""


def devsecops_gitignore() -> str:
    return """dashboard.env
"""


def student_guide(facts: ProjectFacts) -> str:
    container = "se construye y analiza la imagen" if facts.dockerfile else "se registra como no aplicable porque no hay Dockerfile"
    return f"""# Guía DevSecOps del proyecto

Paquete DevSecOps instalado: **{DEVSECOPS_VERSION}**.

## Qué se ha detectado

- Perfil: {facts.profile_name}
- Construcción: {facts.build_system}
- Java: {facts.java_version}
- Contenedores: {container}

## Cuándo se ejecuta

El workflow se ejecuta con cada cambio y también cada lunes a las 06:00 UTC. La ejecución semanal permite detectar vulnerabilidades publicadas después del último commit.

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
        "devsecopsVersion": DEVSECOPS_VERSION,
        "generatedAt": date.today().isoformat(),
        "profile": facts.public(),
        "capabilities": {"securityPipeline": True, "localDashboard": include_dashboard},
    }, ensure_ascii=False, indent=2)
