from fractions import Fraction
import json
import tempfile
import unittest
from pathlib import Path

from dicethrone_helper.analysis import analyze_character, write_analysis
from dicethrone_helper.character import CharacterConfig
from tests.helpers import symbol_config


class AnalysisTests(unittest.TestCase):
    def test_analysis_contains_every_state_and_an_exact_global_probability(self) -> None:
        character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Probabilités contrôlées",
                "symbols": symbol_config("ABBBBB"),
                "abilities": [{"name": "Cinq A", "symbols": "AAAAA"}],
            }
        )

        analysis = analyze_character(character)

        self.assertEqual(analysis["schema_version"], 1)
        self.assertEqual(len(analysis["states"]), 252)
        self.assertEqual(
            sum(
                Fraction(
                    state["initial_probability"]["numerator"],
                    state["initial_probability"]["denominator"],
                )
                for state in analysis["states"]
            ),
            Fraction(1),
        )
        global_probability = analysis["global"][0]["probability"]
        exact_global = Fraction(
            global_probability["numerator"], global_probability["denominator"]
        )
        self.assertEqual(exact_global, Fraction(91, 216) ** 5)
        success_by_roll = analysis["global"][0]["success_by_roll"]
        self.assertEqual(
            sum(Fraction(item["numerator"], item["denominator"]) for item in success_by_roll),
            exact_global,
        )

    def test_written_analysis_is_valid_json(self) -> None:
        character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Minimal",
                "symbols": symbol_config("AAAAAA"),
                "abilities": [{"name": "Un A", "symbols": "A"}],
            }
        )
        analysis = analyze_character(character)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "analysis.json"
            write_analysis(analysis, destination)
            restored = json.loads(destination.read_text(encoding="utf-8"))

        self.assertEqual(restored["character"]["name"], "Minimal")
        self.assertEqual(restored["states"][0]["dice"], [1, 1, 1, 1, 1])

    def test_second_roll_policy_contains_exact_accidental_outcomes(self) -> None:
        character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Issues contrôlées",
                "symbols": symbol_config("ABCDEF"),
                "abilities": [
                    {"name": "Cinq A", "symbols": "AAAAA"},
                    {"name": "Un B", "symbols": "B"},
                    {"name": "Un C*", "symbols": "C"},
                ],
            }
        )

        analysis = analyze_character(character)
        state = next(item for item in analysis["states"] if item["dice"] == [1, 1, 1, 1, 2])
        policy = state["after_second_roll"]["cinq-a"]

        self.assertEqual(policy["actions"][0]["reroll_faces"], [2])
        self.assertEqual(
            policy["reroll_outcomes"],
            {
                "nothing": {"numerator": 1, "denominator": 2},
                "nothing_without_upgraded_abilities": {
                    "numerator": 2,
                    "denominator": 3,
                },
                "accidental_abilities": [
                    {
                        "ability_id": "un-b",
                        "probability": {"numerator": 1, "denominator": 6},
                    },
                    {
                        "ability_id": "un-c-",
                        "probability": {"numerator": 1, "denominator": 6},
                    },
                ],
            },
        )

    def test_equal_target_chances_prefer_the_action_with_the_lowest_whiff(self) -> None:
        character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Départage contrôlé",
                "symbols": symbol_config("ABCDEF"),
                "abilities": [
                    {"name": "Petite suite", "straight": "small"},
                    {"name": "Fiesta", "straight": "large"},
                ],
            }
        )

        analysis = analyze_character(character)
        state = next(item for item in analysis["states"] if item["dice"] == [1, 2, 3, 4, 6])
        policy = state["after_second_roll"]["fiesta"]

        self.assertEqual(policy["probability"], {"numerator": 1, "denominator": 6})
        self.assertEqual(policy["actions"][0]["reroll_faces"], [6])
        self.assertEqual(
            policy["reroll_outcomes"]["nothing"],
            {"numerator": 0, "denominator": 1},
        )


if __name__ == "__main__":
    unittest.main()
