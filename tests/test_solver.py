from fractions import Fraction
import unittest

from dicethrone_helper.character import CharacterConfig
from dicethrone_helper.solver import ExactSolver


class ExactSolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Probabilités contrôlées",
                "symbols": "ABBBBB",
                "abilities": [{"name": "Cinq A", "symbols": "AAAAA"}],
            }
        )
        self.ability = self.character.abilities[0]
        self.solver = ExactSolver(self.character)

    def test_one_missing_symbol_with_one_reroll_has_one_in_six_chance(self) -> None:
        policy = self.solver.solve(self.ability, (1, 1, 1, 1, 2), rerolls=1)

        self.assertEqual(policy.probability, Fraction(1, 6))
        self.assertEqual(policy.expected_additional_rolls, Fraction(1, 1))
        self.assertEqual(policy.primary_action.reroll, (2,))

    def test_two_rerolls_adapt_after_the_first_failure(self) -> None:
        policy = self.solver.solve(self.ability, (1, 1, 1, 1, 2), rerolls=2)

        self.assertEqual(policy.probability, Fraction(11, 36))
        self.assertEqual(policy.expected_additional_rolls, Fraction(11, 6))
        self.assertEqual(policy.success_by_roll, (Fraction(1, 6), Fraction(5, 36)))
        self.assertEqual(policy.primary_action.reroll, (2,))

    def test_completed_ability_stops_without_rerolling(self) -> None:
        policy = self.solver.solve(self.ability, (1, 1, 1, 1, 1), rerolls=2)

        self.assertEqual(policy.probability, Fraction(1, 1))
        self.assertTrue(policy.success_now)
        self.assertEqual(policy.actions, ())


if __name__ == "__main__":
    unittest.main()
