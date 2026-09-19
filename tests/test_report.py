import unittest

from dicethrone_helper.analysis import analyze_character
from dicethrone_helper.character import CharacterConfig
from dicethrone_helper.report import render_report


class ReportTests(unittest.TestCase):
    def test_report_is_self_contained_and_contains_both_static_indexes(self) -> None:
        character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Personnage <test>",
                "symbols": "AAAAAA",
                "abilities": [{"name": "Capacité & test", "symbols": "A"}],
            }
        )
        analysis = analyze_character(character)

        report = render_report(analysis)

        self.assertIn("<title>Personnage &lt;test&gt;</title>", report)
        self.assertIn("<h1>Personnage &lt;test&gt;</h1>", report)
        self.assertNotIn("Aide à la relance", report)
        self.assertIn("Capacité &amp; test", report)
        self.assertIn("Après le premier lancer", report)
        self.assertIn("Après le deuxième lancer", report)
        self.assertIn(
            "Analyse exhaustive des probabilités d’activation des capacités : "
            "Consultez la synthèse globale ou saisissez le résultat de vos cinq dés, "
            "puis consultez « Premier lancer » ou « Deuxième lancer » selon l’étape du tour.",
            report,
        )
        self.assertIn('placeholder="ex. 12346"', report)
        self.assertIn("Saisir cinq chiffres, dans n’importe quel ordre", report)
        self.assertIn('class="section-links"', report)
        self.assertIn("align-items:flex-start", report)
        self.assertIn("scroll-padding-top:var(--anchor-offset,6rem)", report)
        self.assertIn("new ResizeObserver(updateAnchorOffset).observe(navigation)", report)
        self.assertIn("body.is-filtering #overview", report)
        self.assertIn("document.body.classList.toggle('is-filtering', Boolean(roll))", report)
        self.assertIn('data-numerator="1" data-denominator="1"', report)
        self.assertIn("const rankSecondRoll = roll =>", report)
        self.assertIn("secondRoll.append(section)", report)
        self.assertIn("const scheduleApply = () =>", report)
        self.assertIn("window.setTimeout(apply, 150)", report)
        self.assertIn("if (rollInput.value.length === 5)", report)
        self.assertIn("document.body.classList.contains('is-filtering')", report)
        self.assertNotIn("Tout déplier", report)
        self.assertNotIn("Tout replier", report)
        self.assertNotIn("window.print", report)
        self.assertNotIn("https://", report)
        self.assertNotIn("http://", report)

    def test_report_shows_nothing_and_accidental_ability_probabilities(self) -> None:
        character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Issues contrôlées",
                "symbols": "ABCDEF",
                "abilities": [
                    {"name": "Cinq A", "symbols": "AAAAA"},
                    {"name": "Un B", "symbols": "B"},
                    {"name": "Un C*", "symbols": "C"},
                ],
            }
        )

        report = render_report(analyze_character(character))

        self.assertIn("Issues de cette relance", report)
        self.assertIn("💀 Whiff&nbsp;: <strong>67&nbsp;%</strong>", report)
        self.assertNotIn("Rien du tout", report)
        self.assertIn("Un B&nbsp;: <strong>17&nbsp;%</strong>", report)
        self.assertIn('id="upgraded-filter"', report)
        self.assertIn('data-upgraded="true"', report)
        self.assertIn('class="without-upgraded"', report)
        self.assertIn('class="with-upgraded"', report)
        self.assertIn("upgradedInput.addEventListener('change', apply)", report)


if __name__ == "__main__":
    unittest.main()
