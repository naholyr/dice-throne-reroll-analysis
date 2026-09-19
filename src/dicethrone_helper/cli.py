from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .analysis import analyze_character, write_analysis
from .character import ConfigError, load_character
from .report import load_analysis, write_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dicethrone-helper",
        description="Calcule exactement les meilleures relances de Dice Throne.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze", help="Générer l'artefact probabiliste durable d'un personnage."
    )
    analyze.add_argument("character", type=Path, help="Configuration JSON du personnage.")
    analyze.add_argument("--output", "-o", type=Path, required=True)

    report = subparsers.add_parser(
        "report", help="Générer un rapport HTML depuis un artefact existant."
    )
    report.add_argument("analysis", type=Path, help="Artefact JSON produit par analyze.")
    report.add_argument("--output", "-o", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "analyze":
            character = load_character(args.character)
            print(f"Analyse exacte de {character.name}…")
            write_analysis(analyze_character(character), args.output)
            print(f"Artefact écrit dans {args.output}")
        else:
            analysis = load_analysis(args.analysis)
            write_report(analysis, args.output)
            print(f"Rapport écrit dans {args.output}")
    except (ConfigError, ValueError, OSError) as error:
        print(f"Erreur: {error}", file=sys.stderr)
        return 2
    return 0
