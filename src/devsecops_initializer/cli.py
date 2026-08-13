from __future__ import annotations

import argparse
import json
from pathlib import Path

from .service import DEFAULT_WORKFLOW_REPOSITORY, InitializerService


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Incorpora una base DevSecOps educativa en un proyecto existente.")
    commands = result.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Detecta el proyecto y muestra el plan sin modificarlo.")
    inspect.add_argument("project", type=Path)
    generate = commands.add_parser("generate", help="Genera una copia ZIP con los controles incorporados.")
    generate.add_argument("project", type=Path)
    generate.add_argument("output", type=Path)
    generate.add_argument("--workflow-repository", default=DEFAULT_WORKFLOW_REPOSITORY)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    service = InitializerService()
    if args.command == "inspect":
        print(json.dumps(service.analyze(args.project).public(), ensure_ascii=False, indent=2))
        return 0
    args.output.write_bytes(service.generate_zip(args.project, args.workflow_repository))
    print(f"Proyecto generado: {args.output}")
    return 0

