from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .analysis import analyze_character, write_analysis
from .character import ConfigError, load_character
from .karnyx import KarnyxExtractionError, write_extractions
from .matchup_report import (
    MatchupReportError,
    write_all_matchup_reports,
    write_matchup_report,
)
from .report import load_analysis, load_matchup_heroes, write_index, write_report


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

    index = subparsers.add_parser(
        "index", help="Générer la page d'accueil d'un ensemble de rapports."
    )
    index.add_argument("analyses", nargs="+", type=Path)
    index.add_argument("--output", "-o", type=Path, required=True)
    index.add_argument("--matchup-heroes-dir", type=Path, default=Path("characters/karnyx"))

    extract = subparsers.add_parser(
        "extract-karnyx", help="Extraire les statistiques des pages HTML Karnyx."
    )
    extract.add_argument("html", nargs="+", type=Path)
    extract.add_argument("--output", "-o", type=Path, required=True)
    extract.add_argument(
        "--skip-up-to-date",
        action="store_true",
        help="Ne pas régénérer les JSON plus récents que leur HTML.",
    )

    matchups = subparsers.add_parser(
        "matchups", help="Générer un rapport de matchups pour une équipe de trois héros."
    )
    matchups.add_argument("team", nargs="*", metavar="HERO_SLUG")
    matchups.add_argument(
        "--all", action="store_true", help="Générer toutes les équipes de trois possibles."
    )
    matchups.add_argument(
        "--skip-up-to-date",
        action="store_true",
        help="Ne pas régénérer les rapports plus récents que leurs trois JSON.",
    )
    matchups.add_argument("--heroes-dir", type=Path, default=Path("characters/karnyx"))
    matchups.add_argument(
        "--output-dir", type=Path, default=Path("generated-website/matchups")
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "analyze":
            character = load_character(args.character)
            print(f"Analyse exacte de {character.name}…")
            write_analysis(analyze_character(character), args.output)
            print(f"Artefact écrit dans {args.output}")
        elif args.command == "report":
            analysis = load_analysis(args.analysis)
            write_report(analysis, args.output)
            print(f"Rapport écrit dans {args.output}")
        elif args.command == "extract-karnyx":
            outputs = write_extractions(
                args.html,
                args.output,
                skip_if_up_to_date=args.skip_up_to_date,
            )
            for output in outputs:
                print(f"Données Karnyx écrites dans {output}")
        elif args.command == "matchups":
            if args.all:
                outputs = write_all_matchup_reports(
                    args.heroes_dir,
                    args.output_dir,
                    skip_if_up_to_date=args.skip_up_to_date,
                )
                print(f"{len(outputs)} rapports de matchups écrits dans {args.output_dir}")
            else:
                output = write_matchup_report(
                    args.team,
                    args.heroes_dir,
                    args.output_dir,
                    skip_if_up_to_date=args.skip_up_to_date,
                )
                print(f"Rapport de matchups écrit dans {output}")
        else:
            analyses = [(path, load_analysis(path)) for path in args.analyses]
            write_index(
                analyses,
                args.output,
                matchup_heroes=load_matchup_heroes(args.matchup_heroes_dir),
            )
            print(f"Index écrit dans {args.output}")
    except (
        ConfigError,
        KarnyxExtractionError,
        MatchupReportError,
        ValueError,
        OSError,
    ) as error:
        print(f"Erreur: {error}", file=sys.stderr)
        return 2
    return 0
