from __future__ import annotations

import base64
import html
import json
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def _embedded_font_css() -> str:
    fonts = Path(__file__).with_name("fonts")

    def encoded(filename: str) -> str:
        return base64.b64encode((fonts / filename).read_bytes()).decode("ascii")

    return (
        '@font-face{font-family:"League Spartan";font-style:normal;'
        'font-weight:200 900;font-display:swap;'
        f'src:url(data:font/woff2;base64,{encoded("league-spartan-latin.woff2")}) '
        'format("woff2")}'
        '@font-face{font-family:"Roboto Condensed";font-style:normal;'
        'font-weight:100 900;font-display:swap;'
        f'src:url(data:font/woff2;base64,{encoded("roboto-condensed-latin.woff2")}) '
        'format("woff2")}'
    )


@lru_cache(maxsize=1)
def _embedded_font_license() -> str:
    fonts = Path(__file__).with_name("fonts")
    league_license = (fonts / "LICENSE-League-Spartan.txt").read_text(
        encoding="utf-8"
    )
    roboto_license = (fonts / "LICENSE-Roboto-Condensed.txt").read_text(
        encoding="utf-8"
    )
    roboto_copyright = roboto_license.splitlines()[0]
    return html.escape(roboto_copyright + "\n\n" + league_license)


def _as_fraction(raw: dict[str, int]) -> Fraction:
    return Fraction(raw["numerator"], raw["denominator"])


def _integer_percent(raw: dict[str, int]) -> int:
    percentage = _as_fraction(raw) * 100
    return (2 * percentage.numerator + percentage.denominator) // (
        2 * percentage.denominator
    )


def _precise_percent(raw: dict[str, int]) -> str:
    value = float(_as_fraction(raw) * 100)
    return f"{value:.6f}".replace(".", ",")


def _exact(raw: dict[str, int]) -> str:
    return f"{raw['numerator']}/{raw['denominator']}"


def _dice_label(dice: list[int]) -> str:
    return "–".join(str(face) for face in dice)


def _is_upgraded(ability: dict[str, Any]) -> bool:
    return bool(ability.get("upgraded", ability["name"].endswith("*")))


def _upgraded_attribute(ability: dict[str, Any]) -> str:
    return str(_is_upgraded(ability)).lower()


def _items_label(items: list[Any]) -> str:
    return " · ".join(html.escape(str(item)) for item in items) if items else "—"


def _action_label(policy: dict[str, Any]) -> str:
    if policy["success_now"]:
        return '<span class="done">Déjà obtenue · aucune relance</span>'
    actions = policy["actions"]
    if not actions:
        return '<span class="impossible">Aucune relance disponible</span>'
    primary = actions[0]
    label = (
        f'<span class="keep">Garder&nbsp;: {_items_label(primary["keep"])}</span>'
        f'<span class="reroll">Relancer&nbsp;: {_items_label(primary["reroll"])}</span>'
    )
    if len(actions) > 1:
        alternatives = "; ".join(
            f"garder {_items_label(action['keep'])}, relancer {_items_label(action['reroll'])}"
            for action in actions[1:]
        )
        label += (
            '<details class="ties"><summary>'
            f"{len(actions) - 1} autre(s) choix optimal(aux)</summary>"
            f"<span>{alternatives}</span></details>"
        )
    return label


def _probability_cell(policy: dict[str, Any]) -> str:
    probability = policy["probability"]
    return (
        f'<strong class="percent">{_integer_percent(probability)}&nbsp;%</strong>'
        f'<span class="exact">{_precise_percent(probability)}&nbsp;% · '
        f'{_exact(probability)}</span>'
    )


def _reroll_outcomes_label(
    policy: dict[str, Any], ability_by_id: dict[str, dict[str, str]]
) -> str:
    outcomes = policy.get("reroll_outcomes")
    if outcomes is None:
        return ""
    accidental = sorted(
        outcomes["accidental_abilities"],
        key=lambda item: _as_fraction(item["probability"]),
        reverse=True,
    )

    def outcome(
        name: str,
        probability: dict[str, int],
        *,
        css_class: str = "",
        upgraded: bool = False,
    ) -> str:
        details = f"{_precise_percent(probability)} % · {_exact(probability)}"
        class_attribute = f' class="{css_class}"' if css_class else ""
        return (
            f'<span{class_attribute} data-upgraded="{str(upgraded).lower()}" '
            f'title="{details}">{html.escape(name)}&nbsp;: '
            f'<strong>{_integer_percent(probability)}&nbsp;%</strong></span>'
        )

    nothing_without_upgraded = outcomes.get(
        "nothing_without_upgraded_abilities", outcomes["nothing"]
    )
    items = [
        outcome(
            "💀 Whiff", nothing_without_upgraded, css_class="without-upgraded"
        ),
        outcome("💀 Whiff", outcomes["nothing"], css_class="with-upgraded"),
    ]
    items.extend(
        outcome(
            ability_by_id[item["ability_id"]]["name"],
            item["probability"],
            upgraded=_is_upgraded(ability_by_id[item["ability_id"]]),
        )
        for item in accidental
    )
    return (
        '<div class="reroll-outcomes"><b>Issues de cette relance</b>'
        f'{"".join(items)}</div>'
    )


def _ability_row(
    rank: int, ability: dict[str, str], policy: dict[str, Any]
) -> str:
    return (
        f'<tr class="ability-row" data-ability="{html.escape(ability["id"])}" '
        f'data-upgraded="{_upgraded_attribute(ability)}">'
        f'<td class="rank">{rank}</td>'
        f'<th scope="row">{html.escape(ability["name"])}</th>'
        f'<td class="probability">{_probability_cell(policy)}</td>'
        f'<td class="action">{_action_label(policy)}</td>'
        "</tr>"
    )


def _table_header(include_rank: bool = True) -> str:
    rank = '<th scope="col" class="rank">Rang</th>' if include_rank else ""
    return (
        "<thead><tr>"
        f"{rank}<th scope=\"col\">Capacité</th><th scope=\"col\">Chance finale</th>"
        '<th scope="col">Décision optimale</th></tr></thead>'
    )


def render_report(analysis: dict[str, Any]) -> str:
    if analysis.get("schema_version") != 1:
        raise ValueError("Version d'artefact d'analyse non supportée.")
    character = analysis["character"]
    abilities = character["abilities"]
    ability_by_id = {ability["id"]: ability for ability in abilities}
    global_by_id = {item["ability_id"]: item for item in analysis["global"]}

    global_rows: list[str] = []
    ranked_global = sorted(
        abilities,
        key=lambda ability: _as_fraction(global_by_id[ability["id"]]["probability"]),
        reverse=True,
    )
    for rank, ability in enumerate(ranked_global, 1):
        result = global_by_id[ability["id"]]
        by_roll = result["success_by_roll"]
        global_rows.append(
            f'<tr class="global-ability" data-upgraded="{_upgraded_attribute(ability)}">'
            f"<td class=\"rank\">{rank}</td><th scope=\"row\">{html.escape(ability['name'])}</th>"
            f"<td class=\"probability\">{_probability_cell(result)}</td>"
            "<td class=\"timeline\">"
            f"L1 {_integer_percent(by_roll[0])}&nbsp;% · "
            f"L2 {_integer_percent(by_roll[1])}&nbsp;% · "
            f"L3 {_integer_percent(by_roll[2])}&nbsp;%"
            "</td></tr>"
        )

    first_roll_sections: list[str] = []
    for state in analysis["states"]:
        dice_label = _dice_label(state["dice"])
        policies = state["after_first_roll"]
        ranked = sorted(
            abilities,
            key=lambda ability: _as_fraction(policies[ability["id"]]["probability"]),
            reverse=True,
        )
        rows = "".join(
            _ability_row(rank, ability, policies[ability["id"]])
            for rank, ability in enumerate(ranked, 1)
        )
        first_roll_sections.append(
            f'<details class="roll-card" data-roll="{dice_label}" open>'
            f'<summary><span class="dice">{dice_label}</span>'
            f'<span class="occurrence">Apparition&nbsp;: '
            f'{_precise_percent(state["initial_probability"])}&nbsp;%</span></summary>'
            f'<table>{_table_header() }<tbody>{rows}</tbody></table></details>'
        )

    second_roll_sections: list[str] = []
    for ability in abilities:
        rows: list[str] = []
        for state in analysis["states"]:
            policy = state["after_second_roll"][ability["id"]]
            probability = policy["probability"]
            dice_label = _dice_label(state["dice"])
            rows.append(
                f'<tr class="second-state" data-roll="{dice_label}" '
                f'data-numerator="{probability["numerator"]}" '
                f'data-denominator="{probability["denominator"]}">'
                f'<th scope="row" class="dice">{dice_label}</th>'
                f'<td class="probability">{_probability_cell(policy)}</td>'
                f'<td class="action">{_action_label(policy)}'
                f'{_reroll_outcomes_label(policy, ability_by_id)}</td></tr>'
            )
        second_roll_sections.append(
            f'<section class="ability-section" data-ability="{html.escape(ability["id"])}" '
            f'data-upgraded="{_upgraded_attribute(ability)}">'
            f'<h3>{html.escape(ability["name"])}</h3>'
            '<table><thead><tr><th scope="col">Lancer actuel</th>'
            '<th scope="col">Chance finale</th><th scope="col">Dernière relance</th>'
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table></section>"
        )

    ability_options = "".join(
        f'<option value="{html.escape(ability["id"])}" '
        f'data-upgraded="{_upgraded_attribute(ability)}">'
        f'{html.escape(ability["name"])}</option>'
        for ability in abilities
    )
    title = html.escape(character["name"])
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    {_embedded_font_css()}
    :root{{--ink:#182022;--muted:#637174;--paper:#fbfaf6;--card:#fff;--line:#dfe3dc;--accent:#9f2f2f;--accent-soft:#f6e8e2;--good:#246b4b;--shadow:0 8px 30px #17201c10}}
    *{{box-sizing:border-box}} html{{scroll-behavior:smooth;scroll-padding-top:var(--anchor-offset,6rem)}} body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Roboto Condensed",sans-serif;font-size:15px;line-height:1.45}}
    header{{padding:3.5rem max(5vw,1.25rem) 2.5rem;background:linear-gradient(135deg,#232b2b,#3f2725);color:#fff}}
    header p{{max-width:70ch;color:#e7dddd}} h1,h2,h3{{font-family:"League Spartan",sans-serif;font-weight:900;text-transform:uppercase;letter-spacing:-.02em}} h1{{margin:0 0 .5rem;font-size:clamp(2rem,5vw,4.5rem);line-height:1.02}} h2{{margin:3rem 0 1rem;font-size:2rem;line-height:1.1}} h3{{font-size:1.35rem;line-height:1.2}}
    main{{width:min(1500px,94vw);margin:auto;padding-bottom:5rem}} nav{{position:sticky;top:0;z-index:5;display:flex;gap:.7rem;align-items:flex-start;flex-wrap:wrap;padding:.8rem max(3vw,1rem);background:#fbfaf6ee;border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}
    nav label{{display:grid;gap:.2rem;color:var(--muted);font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em}} .filter-hint{{max-width:18rem;font-size:.7rem;font-weight:500;text-transform:none;letter-spacing:0}} input,select{{font:inherit;padding:.55rem .7rem;border:1px solid #bfc8c2;border-radius:.45rem;background:#fff}} nav .upgrade-toggle{{display:flex;align-items:center;gap:.45rem;padding-top:1.65rem;white-space:nowrap;text-transform:none;letter-spacing:0}} nav .upgrade-toggle input{{width:1rem;height:1rem;margin:0;padding:0;accent-color:var(--accent)}} .section-links{{display:flex;gap:.7rem;padding-top:1.33rem;white-space:nowrap}} nav a{{color:var(--accent);font-weight:700;padding:.55rem}}
    .intro{{max-width:80ch;color:var(--muted)}} .summary-table,.roll-card,.ability-section{{background:var(--card);box-shadow:var(--shadow);border:1px solid var(--line);border-radius:.65rem}}
    table{{width:100%;border-collapse:collapse}} th,td{{padding:.65rem .75rem;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}} thead th{{position:sticky;top:4.2rem;background:#f1f2ed;color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}} tbody tr:last-child>*{{border-bottom:0}} .rank{{width:4rem;text-align:center;color:var(--muted)}}
    .percent{{display:block;font-size:1.15rem;color:var(--accent)}} .exact{{display:block;color:var(--muted);font:11px/1.25 ui-monospace,monospace}} .probability{{white-space:nowrap;width:11rem}} .timeline{{white-space:nowrap}}
    .keep,.reroll{{display:inline-block;margin:0 .7rem .2rem 0}} .keep{{color:var(--good);font-weight:700}} .reroll{{color:var(--accent);font-weight:700}} .done{{color:var(--good);font-weight:700}} .ties{{color:var(--muted);font-size:.8rem}} .ties summary{{cursor:pointer}} .reroll-outcomes{{display:grid;gap:.15rem;margin-top:.5rem;padding-top:.5rem;border-top:1px solid var(--line);color:var(--muted);font-size:.8rem}} .reroll-outcomes strong{{color:var(--ink)}}
    .roll-grid{{display:grid;gap:1rem}} .roll-card{{overflow:clip}} .roll-card>summary{{cursor:pointer;display:flex;align-items:center;justify-content:space-between;padding:.85rem 1rem;background:#f4f1eb;list-style:none}} .roll-card>summary::-webkit-details-marker{{display:none}} .dice{{font:700 1rem/1 ui-monospace,monospace;letter-spacing:.06em}} .occurrence{{color:var(--muted);font-size:.8rem}}
    .ability-section{{margin:1.2rem 0;overflow:clip}} .ability-section h3{{margin:0;padding:1rem;background:var(--accent-soft)}} .hidden,body.is-filtering #overview,body:not(.include-upgraded) [data-upgraded="true"],body:not(.include-upgraded) .with-upgraded,body.include-upgraded .without-upgraded{{display:none!important}} .legend{{padding:.85rem 1rem;background:#edf3ef;border-left:4px solid var(--good)}}
    footer{{color:var(--muted);text-align:center;padding:3rem}} .font-licenses{{margin:1rem auto 0;max-width:70rem;text-align:left}} .font-licenses summary{{cursor:pointer;text-align:center}} .font-licenses pre{{white-space:pre-wrap;font:11px/1.35 ui-monospace,monospace}}
    @media(max-width:760px){{nav .upgrade-toggle,.section-links{{flex-basis:100%;padding-top:0}} .rank,.exact{{display:none}} th,td{{padding:.5rem;font-size:.85rem}} .probability{{width:auto}} thead th{{top:7.5rem}}}}
    @media print{{body{{background:#fff;font-size:9pt}} header{{padding:1rem;background:#fff;color:#000;border-bottom:2px solid #000}} header p,nav,footer{{display:none}} main{{width:100%;padding:0}} h2{{break-before:page;margin-top:0}} .roll-card,.ability-section,.summary-table{{box-shadow:none;border:1px solid #999;break-inside:avoid}} .roll-card{{margin:.25rem 0}} .roll-card>summary{{padding:.3rem;background:#eee}} th,td{{padding:.25rem}} thead th{{position:static}} .exact{{font-size:7pt}} .ties{{display:none}}}}
  </style>
</head>
<body>
<header><h1>{title}</h1><p>Analyse exhaustive des probabilités d’activation des capacités : Consultez la synthèse globale ou saisissez le résultat de vos cinq dés, puis consultez « Premier lancer » ou « Deuxième lancer » selon l’étape du tour.</p></header>
<nav aria-label="Filtres du rapport">
  <label>Lancer <input id="roll-filter" inputmode="numeric" pattern="[1-6]{{5}}" placeholder="ex. 12346" aria-describedby="roll-hint"><span id="roll-hint" class="filter-hint">Saisir cinq chiffres, dans n’importe quel ordre</span></label>
  <label>Capacité <select id="ability-filter"><option value="">Toutes</option>{ability_options}</select></label>
  <label class="upgrade-toggle"><input type="checkbox" id="upgraded-filter"> Inclure les capacités améliorées</label>
  <span class="section-links"><a href="#first-roll">Premier lancer</a><a href="#second-roll">Deuxième lancer</a></span>
</nav>
<main>
  <section id="overview"><h2>Synthèse globale</h2><p class="intro">Chance d’obtenir chaque capacité depuis avant le premier lancer, en suivant ensuite sa stratégie optimale. L1, L2 et L3 indiquent le lancer auquel la réussite survient.</p>
    <table class="summary-table"><thead><tr><th class="rank">Rang</th><th>Capacité</th><th>Chance finale</th><th>Réussite par lancer</th></tr></thead><tbody>{''.join(global_rows)}</tbody></table>
  </section>
  <section id="first-roll"><h2>Après le premier lancer</h2><p class="intro">Chaque lancer présente les capacités de la plus sûre à la moins sûre. La stratégie tient déjà compte de la décision optimale qui sera prise après le deuxième lancer.</p>
    <p class="legend">Pour une suite, les décisions utilisent les numéros. Pour une combinaison symbolique, elles utilisent les symboles propres au personnage ({html.escape(character['symbols'])}).</p>
    <div class="roll-grid">{''.join(first_roll_sections)}</div>
  </section>
  <section id="second-roll"><h2>Après le deuxième lancer</h2><p class="intro">Index complet avec une seule relance restante, regroupé par capacité poursuivie. Les issues indiquées correspondent à la relance optimale affichée. Elles peuvent se cumuler&nbsp;: un même résultat peut activer plusieurs capacités.</p>{''.join(second_roll_sections)}</section>
</main>
<footer>Généré par dicethrone-helper {html.escape(analysis['engine']['version'])} · aucune simulation aléatoire<details class="font-licenses"><summary>Licences typographiques</summary><pre>{_embedded_font_license()}</pre></details></footer>
<script>
(() => {{
  const navigation = document.querySelector('nav');
  const rollInput = document.querySelector('#roll-filter');
  const abilityInput = document.querySelector('#ability-filter');
  const upgradedInput = document.querySelector('#upgraded-filter');
  const secondRoll = document.querySelector('#second-roll');
  const secondSections = [...secondRoll.querySelectorAll('.ability-section')];
  const originalSecondOrder = new Map(secondSections.map((section, index) => [section, index]));
  const updateAnchorOffset = () => document.documentElement.style.setProperty(
    '--anchor-offset', `${{navigation.getBoundingClientRect().height + 16}}px`
  );
  new ResizeObserver(updateAnchorOffset).observe(navigation);
  updateAnchorOffset();
  const digits = value => (value.match(/[1-6]/g) || []).slice(0, 5);
  const canonicalRoll = value => {{
    const faces = digits(value);
    return faces.length === 5 ? faces.sort().join('–') : '';
  }};
  const rankSecondRoll = roll => {{
    const probability = section => [...section.querySelectorAll('.second-state')]
      .find(row => row.dataset.roll === roll)?.dataset;
    [...secondSections].sort((left, right) => {{
      if (!roll) return originalSecondOrder.get(left) - originalSecondOrder.get(right);
      const leftProbability = probability(left);
      const rightProbability = probability(right);
      const leftCross = BigInt(leftProbability.numerator) * BigInt(rightProbability.denominator);
      const rightCross = BigInt(rightProbability.numerator) * BigInt(leftProbability.denominator);
      if (leftCross !== rightCross) return leftCross > rightCross ? -1 : 1;
      return originalSecondOrder.get(left) - originalSecondOrder.get(right);
    }}).forEach(section => secondRoll.append(section));
  }};
  const apply = () => {{
    const roll = canonicalRoll(rollInput.value);
    const includeUpgraded = upgradedInput.checked;
    const selectedOption = abilityInput.selectedOptions[0];
    if (!includeUpgraded && selectedOption?.dataset.upgraded === 'true') {{
      abilityInput.value = '';
    }}
    const ability = abilityInput.value;
    document.body.classList.toggle('is-filtering', Boolean(roll));
    document.body.classList.toggle('include-upgraded', includeUpgraded);
    abilityInput.querySelectorAll('[data-upgraded="true"]').forEach(option => {{
      option.disabled = !includeUpgraded;
      option.hidden = !includeUpgraded;
    }});
    let globalRank = 1;
    document.querySelectorAll('.global-ability').forEach(row => {{
      if (includeUpgraded || row.dataset.upgraded !== 'true') {{
        row.querySelector('.rank').textContent = globalRank++;
      }}
    }});
    document.querySelectorAll('.roll-card').forEach(card => {{
      card.classList.toggle('hidden', Boolean(roll) && !card.dataset.roll.includes(roll));
      let visibleRank = 1;
      card.querySelectorAll('.ability-row').forEach(row => {{
        const hidden = Boolean(ability) && row.dataset.ability !== ability;
        row.classList.toggle('hidden', hidden);
        if (!hidden && (includeUpgraded || row.dataset.upgraded !== 'true')) {{
          row.querySelector('.rank').textContent = visibleRank++;
        }}
      }});
    }});
    document.querySelectorAll('.ability-section').forEach(section => {{
      section.classList.toggle('hidden', Boolean(ability) && section.dataset.ability !== ability);
      section.querySelectorAll('.second-state').forEach(row => row.classList.toggle('hidden', Boolean(roll) && !row.dataset.roll.includes(roll)));
    }});
    rankSecondRoll(roll);
  }};
  let applyTimer;
  const scheduleApply = () => {{
    window.clearTimeout(applyTimer);
    applyTimer = window.setTimeout(apply, 150);
  }};
  rollInput.addEventListener('input', () => {{
    rollInput.value = digits(rollInput.value).join('');
    window.clearTimeout(applyTimer);
    if (rollInput.value.length === 5) {{
      scheduleApply();
    }} else if (document.body.classList.contains('is-filtering')) {{
      scheduleApply();
    }}
  }});
  abilityInput.addEventListener('change', () => {{
    window.clearTimeout(applyTimer);
    apply();
  }});
  upgradedInput.addEventListener('change', apply);
  apply();
}})();
</script>
</body>
</html>
"""


def load_analysis(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        analysis = json.loads(source.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Impossible de lire {source}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON invalide dans {source}: {error}") from error
    if analysis.get("schema_version") != 1:
        raise ValueError("Version d'artefact d'analyse non supportée.")
    return analysis


def write_report(analysis: dict[str, Any], destination: str | Path) -> None:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(analysis), encoding="utf-8")
