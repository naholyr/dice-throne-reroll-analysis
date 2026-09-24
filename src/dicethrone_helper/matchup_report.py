from __future__ import annotations

import html
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from . import report as report_module
from .report import _embedded_font_css, _embedded_font_license


NEMESIS_THRESHOLD = 45.0
SWEET_THRESHOLD = 55.0
NOTABLE_LOW_THRESHOLD = 40.0
NOTABLE_HIGH_THRESHOLD = 60.0


class MatchupReportError(ValueError):
    """Raised when a team matchup report cannot be built."""


def _slug(team: list[str]) -> str:
    return "-".join(sorted(team))


def _is_up_to_date(team: list[str], heroes_dir: Path, output_dir: Path) -> bool:
    output = output_dir / f"{_slug(team)}.html"
    if not output.is_file():
        return False
    output_mtime = output.stat().st_mtime
    input_paths = [heroes_dir / f"{slug}.json" for slug in team]
    source_paths = [Path(__file__), Path(report_module.__file__)]
    return all(path.stat().st_mtime < output_mtime for path in input_paths + source_paths)


def _load_hero(heroes_dir: Path, slug: str) -> dict[str, Any]:
    path = heroes_dir / f"{slug}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise MatchupReportError(f"Héros inconnu ou JSON absent: {slug}") from error
    except json.JSONDecodeError as error:
        raise MatchupReportError(f"JSON invalide pour {slug}") from error


def _team_matchups(heroes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_opponent: dict[str, dict[str, Any]] = {}
    for hero in heroes:
        for matchup in hero["matchups"]:
            opponent = matchup["slug"]
            entry = by_opponent.setdefault(
                opponent,
                {"slug": opponent, "name": matchup["name"], "members": []},
            )
            entry["members"].append(
                {
                    "hero": hero["hero"]["name"],
                    "hero_slug": hero["source_file"].removesuffix(".html"),
                    "win_rate": matchup["win_rate"],
                    "opponent_win_rate": matchup["opponent_win_rate"],
                    "matches": matchup["matches"],
                }
            )
    return sorted(by_opponent.values(), key=lambda item: item["name"].lower())


def _classify(value: float) -> str:
    if value <= NOTABLE_LOW_THRESHOLD:
        return "bad"
    if value >= NOTABLE_HIGH_THRESHOLD:
        return "good"
    return "even"


def calculate_matchup_report(team: list[str], heroes_dir: Path) -> dict[str, Any]:
    if len(team) != 3 or len(set(team)) != 3:
        raise MatchupReportError("Une équipe doit contenir exactement 3 héros différents")
    heroes = [_load_hero(heroes_dir, slug) for slug in team]
    matchups = _team_matchups(heroes)

    for opponent in matchups:
        members = opponent["members"]
        opponent["nemesis_count"] = sum(
            member["win_rate"] <= NEMESIS_THRESHOLD for member in members
        )
        opponent["sweet_count"] = sum(
            member["win_rate"] >= SWEET_THRESHOLD for member in members
        )
        opponent["best"] = max(members, key=lambda member: member["win_rate"])
        opponent["worst"] = min(members, key=lambda member: member["win_rate"])
        opponent["spread"] = opponent["best"]["win_rate"] - opponent["worst"]["win_rate"]

    notable = [
        {
            **member,
            "opponent": opponent["name"],
            "opponent_slug": opponent["slug"],
            "classification": _classify(member["win_rate"]),
        }
        for opponent in matchups
        for member in opponent["members"]
        if member["win_rate"] <= NOTABLE_LOW_THRESHOLD
        or member["win_rate"] >= NOTABLE_HIGH_THRESHOLD
    ]
    notable.sort(key=lambda item: item["win_rate"])
    return {
        "schema_version": 1,
        "team": [
            {"slug": slug, "name": hero["hero"]["name"]}
            for slug, hero in zip(team, heroes, strict=True)
        ],
        "matchups": matchups,
        "notable": notable,
    }


def _percent(value: float) -> str:
    return f"{value:.2f}%".rstrip("0").rstrip(".")


def _member_cell(member: dict[str, Any]) -> str:
    value = member["win_rate"]
    return (
        f'<span class="rate {_classify(value)}">{_percent(value)}</span>'
        f'<small>{member["matches"]} games</small>'
    )


def _summary_card(title: str, value: str, detail: str, css_class: str = "") -> str:
    return (
        f'<article class="summary-card {css_class}"><strong>{value}</strong>'
        f'<h3>{title}</h3><p>{detail}</p></article>'
    )


def render_matchup_report(report: dict[str, Any]) -> str:
    team = report["team"]
    matchups = report["matchups"]
    nemeses = [item for item in matchups if item["nemesis_count"] >= 2]
    sweets = [item for item in matchups if item["sweet_count"] >= 2]
    notable = report["notable"]
    team_names = " / ".join(item["name"] for item in team)

    def opponent_list(items: list[dict[str, Any]], count_key: str) -> str:
        if not items:
            return '<p class="empty">Aucun adversaire dans cette categorie.</p>'

        def member_class(member: dict[str, Any]) -> str:
            if member["win_rate"] <= NOTABLE_LOW_THRESHOLD:
                return "bad"
            if member["win_rate"] >= NOTABLE_HIGH_THRESHOLD:
                return "good"
            if count_key == "sweet_count" and member["win_rate"] >= SWEET_THRESHOLD:
                return "good"
            if count_key == "nemesis_count" and member["win_rate"] <= NEMESIS_THRESHOLD:
                return "bad"
            return "muted"

        rows = []
        for item in sorted(items, key=lambda value: (-value[count_key], value["name"])):
            details = "".join(
                f'<span class="rate {member_class(member)}">{html.escape(member["hero"])} {_percent(member["win_rate"])}</span>'
                for member in sorted(item["members"], key=lambda value: value["win_rate"])
            )
            rows.append(
                f'<li><div><strong>{html.escape(item["name"])}</strong>'
                f'<small>{item[count_key]} membres concernés</small></div>'
                f'<div class="member-rates">{details}</div></li>'
            )
        return f'<ul class="compact-list">{"".join(rows)}</ul>'

    matrix_header = "".join(f'<th>{html.escape(item["name"])}</th>' for item in team)
    matrix_rows = []
    for opponent in sorted(matchups, key=lambda item: (-item["nemesis_count"], item["name"])):
        cells = "".join(f'<td>{_member_cell(member)}</td>' for member in opponent["members"])
        marker = " nemesis" if opponent["nemesis_count"] >= 2 else " sweet" if opponent["sweet_count"] >= 2 else ""
        matrix_rows.append(
            f'<tr class="{marker}"><th scope="row">{html.escape(opponent["name"])}</th>'
            f'{cells}<td class="best-choice">{html.escape(opponent["best"]["hero"])} '
            f'<b>{_percent(opponent["best"]["win_rate"])}</b></td>'
            f'<td>{_percent(opponent["spread"])}</td></tr>'
        )

    notable_rows = "".join(
        f'<tr><td>{html.escape(item["hero"])}</td><td>{html.escape(item["opponent"])}</td>'
        f'<td><span class="rate {item["classification"]}">{_percent(item["win_rate"])}</span></td>'
        f'<td>{item["matches"]}</td></tr>'
        for item in notable
    ) or '<tr><td colspan="4" class="empty">Aucun matchup ne franchit ces seuils.</td></tr>'

    css = f"""
{_embedded_font_css()}
:root{{--paper:#f3eee5;--ink:#1e2528;--muted:#6c7475;--line:#d8d0c4;--panel:#fffaf2;--teal:#147d78;--red:#b84b4b;--gold:#b47a2b}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Roboto Condensed",sans-serif;font-size:17px;line-height:1.4}}
main{{max-width:1280px;margin:0 auto;padding:3rem 1.25rem 5rem}} h1,h2,h3{{font-family:"League Spartan",sans-serif;margin:0}} h1{{font-size:clamp(2.5rem,6vw,5rem);line-height:.95;max-width:900px}} h2{{font-size:2rem;margin-bottom:.35rem}} h3{{font-size:1.2rem}} p{{color:var(--muted);margin:.35rem 0}} .eyebrow{{color:var(--teal);font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:.75rem}}
.intro{{display:flex;justify-content:space-between;gap:2rem;align-items:end;border-bottom:2px solid var(--ink);padding-bottom:2rem}} .intro p{{max-width:620px;font-size:1.15rem}} .team{{font-family:"League Spartan";font-size:1.15rem;text-align:right;max-width:300px}}
.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.5rem 0 3rem}} .summary-card{{background:var(--panel);border:1px solid var(--line);padding:1.25rem;border-top:5px solid var(--teal)}} .summary-card.danger{{border-top-color:var(--red)}} .summary-card.gold{{border-top-color:var(--gold)}} .summary-card strong{{display:block;font:700 2.7rem/1 "League Spartan"}} .summary-card p{{font-size:.95rem}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin:1rem 0 3rem}} .panel{{background:var(--panel);border:1px solid var(--line);padding:1.25rem}} .panel>p{{margin-bottom:1rem}} .compact-list{{list-style:none;padding:0;margin:0}} .compact-list li{{display:flex;justify-content:space-between;gap:1rem;border-top:1px solid var(--line);padding:.75rem 0}} .compact-list li>div:first-child{{display:flex;flex-direction:column}} .compact-list small,td small{{display:block;color:var(--muted);font-size:.82rem}} .member-rates{{display:flex;gap:.75rem;flex-wrap:wrap;justify-content:end;color:var(--muted)}}
.table-wrap{{overflow:auto;background:var(--panel);border:1px solid var(--line)}} table{{width:100%;border-collapse:collapse;min-width:760px}} th,td{{padding:.7rem .8rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}} thead th{{background:#e8dfd1;font-family:"League Spartan";font-size:.9rem}} tbody th{{font-family:"League Spartan";white-space:nowrap}} tbody tr.nemesis{{background:#f9e9e7}} tbody tr.sweet{{background:#e7f2ee}} .rate{{font:700 1.1rem "League Spartan"}} .rate.good{{color:var(--teal);font-weight:700}} .rate.bad{{color:var(--red);font-weight:700}} .rate.even{{color:var(--ink);font-weight:700}} .rate.muted{{color:var(--muted);font-weight:400;opacity:.75}} td .rate+small{{margin-top:.15rem}} .best-choice b{{color:var(--teal)}}
.legend{{display:flex;gap:1rem;flex-wrap:wrap;color:var(--muted);font-size:.9rem;margin:1rem 0}} .legend span::before{{content:"";display:inline-block;width:.7rem;height:.7rem;margin-right:.35rem;background:currentColor}} .legend .good{{color:var(--teal)}} .legend .bad{{color:var(--red)}} .legend .even{{color:var(--gold)}} .empty{{padding:1rem;text-align:center;font-style:italic}}
footer{{margin-top:3rem;border-top:1px solid var(--line);padding-top:1rem;color:var(--muted);font-size:.8rem}} @media(max-width:800px){{main{{padding-top:2rem}} .intro{{display:block}} .team{{text-align:left;margin-top:1rem}} .summary{{grid-template-columns:repeat(2,1fr)}} .grid{{grid-template-columns:1fr}}}}
@media(max-width:480px){{.summary{{grid-template-columns:1fr 1fr;gap:.5rem}} .summary-card{{padding:.8rem}} .summary-card strong{{font-size:2rem}}}}
"""
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Matchups - {html.escape(team_names)}</title><style>{css}</style></head><body><main>
<header class="intro"><div><div class="eyebrow">Dice Throne · préparation de draft</div><h1>{html.escape(team_names)}</h1><p>Une vue de préparation pour repérer les menaces communes, les cibles favorables et les duels qui méritent d'être mémorisés avant les bans.</p></div><div class="team">Équipe analysée<br><span>{html.escape(team_names)}</span></div></header>
<section class="summary">{_summary_card("Némésis", str(len(nemeses)), "adversaires dangereux contre au moins 2 héros", "danger")}{_summary_card("Sweets", str(len(sweets)), "adversaires favorables contre au moins 2 héros", "gold")}{_summary_card("Matchups notables", str(len(notable)), "duels à 40% ou moins, ou 60% ou plus")}{_summary_card("Adversaires comparés", str(len(matchups)), "tous les héros du pool, y compris les mirror matches")}</section>
<section class="grid"><article class="panel"><h2>Némésis</h2><p>Priorité de ban ou de préparation : ces héros peuvent mettre en difficulté plusieurs membres de l'équipe.</p>{opponent_list(nemeses, "nemesis_count")}</article><article class="panel"><h2>Sweets</h2><p>Cibles à privilégier : plusieurs membres de l'équipe ont un avantage statistique clair.</p>{opponent_list(sweets, "sweet_count")}</article></section>
<section><h2>Matrice de préparation</h2><p>Chaque pourcentage est la chance de victoire du héros de votre équipe. La colonne “meilleur choix” indique le héros à privilégier si cet adversaire arrive dans le trio.</p><div class="legend"><span class="good">60%+ très favorable</span><span class="even">entre les deux seuils</span><span class="bad">40%- très défavorable</span></div><div class="table-wrap"><table><thead><tr><th>Adversaire</th>{matrix_header}<th>Meilleur choix</th><th>Écart équipe</th></tr></thead><tbody>{''.join(matrix_rows)}</tbody></table></div></section>
<section class="panel" style="margin-top:3rem"><h2>Matchups à retenir</h2><p>Les extrêmes sont les plus utiles à mémoriser. Les échantillons sont affichés pour garder le contexte statistique.</p><div class="table-wrap"><table><thead><tr><th>Votre héros</th><th>Adversaire</th><th>Votre winrate</th><th>Parties</th></tr></thead><tbody>{notable_rows}</tbody></table></div></section>
<footer>Seuils : némésis/sweet à 45%/55% sur au moins 2 héros; matchup notable à 40% ou 60%. {_embedded_font_license()}</footer>
</main></body></html>'''


def write_matchup_report(
    team: list[str],
    heroes_dir: Path,
    output_dir: Path,
    *,
    skip_if_up_to_date: bool = False,
) -> Path:
    if skip_if_up_to_date and _is_up_to_date(team, heroes_dir, output_dir):
        return output_dir / f"{_slug(team)}.html"
    report = calculate_matchup_report(team, heroes_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{_slug(team)}.html"
    output.write_text(render_matchup_report(report), encoding="utf-8")
    return output


def write_all_matchup_reports(
    heroes_dir: Path,
    output_dir: Path,
    *,
    skip_if_up_to_date: bool = False,
) -> list[Path]:
    slugs = sorted(path.stem for path in heroes_dir.glob("*.json"))
    if len(slugs) < 3:
        raise MatchupReportError("Au moins 3 fichiers JSON de héros sont nécessaires")
    return [
        write_matchup_report(
            list(team), heroes_dir, output_dir, skip_if_up_to_date=skip_if_up_to_date
        )
        for team in combinations(slugs, 3)
    ]