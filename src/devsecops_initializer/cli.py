from __future__ import annotations

import argparse
import json
from pathlib import Path

from .service import InitializerService


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Incorpora una base DevSecOps en un proyecto existente.")
    commands = result.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser(
        "inspect",
        help="Detecta el proyecto y muestra el plan sin modificarlo.",
    )
    inspect.add_argument("project", type=Path)
    inspect.add_argument(
        "--with-dashboard",
        action="store_true",
        help="Incluye el panel local y la remediación con IA.",
    )

    generate = commands.add_parser(
        "generate",
        help="Genera una copia ZIP con los controles incorporados.",
    )
    generate.add_argument("project", type=Path)
    generate.add_argument("output", type=Path)
    generate.add_argument(
        "--with-dashboard",
        action="store_true",
        help="Incluye el panel local y la remediación con IA.",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    service = InitializerService()
    if args.command == "inspect":
        plan = service.analyze(args.project, args.with_dashboard).public()
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    generated_zip = service.generate_zip(
        args.project,
        args.with_dashboard,
    )
    args.output.write_bytes(generated_zip)
    print(f"Proyecto generado: {args.output}")
    return 0
