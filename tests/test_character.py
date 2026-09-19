import json
import tempfile
import unittest
from pathlib import Path

from dicethrone_helper.character import CharacterConfig, load_character


class CharacterConfigTests(unittest.TestCase):
    def test_loads_symbol_and_straight_abilities(self) -> None:
        payload = {
            "schema_version": 1,
            "name": "Chasseresse",
            "symbols": "AABBCD",
            "abilities": [
                {"name": "Bestiale 1", "symbols": "AAA"},
                {"name": "Charge 1", "straight": "small"},
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "character.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            character = load_character(path)

        self.assertEqual(
            character,
            CharacterConfig.from_dict(payload),
        )
        self.assertEqual(character.symbol_for_face(1), "A")
        self.assertEqual(character.symbol_for_face(6), "D")
        self.assertEqual(character.abilities[0].identifier, "bestiale-1")


if __name__ == "__main__":
    unittest.main()
