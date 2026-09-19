import unittest

from dicethrone_helper.character import Ability, CharacterConfig
from dicethrone_helper.rules import is_success


class RuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Test",
                "symbols": "AABBCD",
                "abilities": [{"name": "Placeholder", "symbols": "A"}],
            }
        )

    def test_symbol_requirements_are_minimum_counts(self) -> None:
        ability = Ability("Sauvage", "symbols", "BBBD", "sauvage")

        self.assertTrue(is_success(self.character, ability, (3, 3, 4, 6, 6)))
        self.assertFalse(is_success(self.character, ability, (3, 4, 5, 5, 6)))

    def test_small_straight_accepts_any_four_consecutive_faces(self) -> None:
        ability = Ability("Charge 1", "straight", "small", "charge-1")

        self.assertTrue(is_success(self.character, ability, (1, 2, 3, 4, 4)))
        self.assertTrue(is_success(self.character, ability, (2, 3, 4, 5, 6)))
        self.assertFalse(is_success(self.character, ability, (1, 2, 3, 5, 6)))

    def test_large_straight_requires_five_consecutive_faces(self) -> None:
        ability = Ability("Charge 2", "straight", "large", "charge-2")

        self.assertTrue(is_success(self.character, ability, (1, 2, 3, 4, 5)))
        self.assertTrue(is_success(self.character, ability, (2, 3, 4, 5, 6)))
        self.assertFalse(is_success(self.character, ability, (1, 2, 3, 4, 6)))

    def test_face_mapping_comes_from_each_character_distribution(self) -> None:
        ability = Ability("Deux A", "symbols", "AA", "deux-a")
        other_character = CharacterConfig.from_dict(
            {
                "schema_version": 1,
                "name": "Autre distribution",
                "symbols": "ABBCCD",
                "abilities": [{"name": "Deux A", "symbols": "AA"}],
            }
        )

        self.assertTrue(is_success(self.character, ability, (1, 2, 3, 4, 5)))
        self.assertFalse(is_success(other_character, ability, (1, 2, 3, 4, 5)))


if __name__ == "__main__":
    unittest.main()
