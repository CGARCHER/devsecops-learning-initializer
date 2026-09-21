from __future__ import annotations

import json
from datetime import date
from importlib.resources import files

from .models import ProjectFacts
from .versioning import DEVSECOPS_VERSION


def _template(name: str) -> str:
    """Carga una plantilla incluida en el paquete, sin depender del directorio actual."""
    return files("devsecops_initializer").joinpath("template_files", name).read_text(encoding="utf-8")


def ruleset_text(branch: str) -> str:
    """Crea el ruleset mínimo para proteger main o develop."""
    include = [f"refs/heads/{branch}"]
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
                    "dismiss_stale_reviews_on_push": True,
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
    return _template("security_setup.md")


def config_text(facts: ProjectFacts, include_dashboard: bool = False) -> str:
    """Genera la configuración común del paquete DevSecOps autónomo."""
    dockerfile = facts.dockerfile or "auto"
    return _template("config.yml").format(
        devsecops_version=DEVSECOPS_VERSION,
        facts_profile_id=facts.profile_id,
        facts_build_system=facts.build_system,
        facts_java_version=facts.java_version,
        dockerfile=dockerfile,
        dashboard_enabled=str(include_dashboard).lower(),
    )


def dashboard_compose() -> str:
    return _template("compose.security.yml")


def dashboard_environment() -> str:
    return _template("dashboard.env.example")


def dashboard_guide() -> str:
    return _template("dashboard.md")


def devsecops_gitignore() -> str:
    return """dashboard.env
"""


def student_guide(facts: ProjectFacts) -> str:
    container = "se construye y analiza la imagen" if facts.dockerfile else "se registra como no aplicable porque no hay Dockerfile"
    return _template("student_guide.md").format(
        devsecops_version=DEVSECOPS_VERSION,
        facts_profile_name=facts.profile_name,
        facts_build_system=facts.build_system,
        facts_java_version=facts.java_version,
        container=container,
    )


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
