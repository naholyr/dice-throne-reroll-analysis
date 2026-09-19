import json
import tempfile
import unittest
from pathlib import Path

from dicethrone_helper.cli import main


class CliTests(unittest.TestCase):
    def test_analyze_then_report_workflow(self) -> None:
        character = {
            "schema_version": 1,
            "name": "CLI",
            "symbols": "AAAAAA",
            "abilities": [{"name": "Un A", "symbols": "A"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            character_path = root / "character.json"
            analysis_path = root / "analysis.json"
            report_path = root / "report.html"
            character_path.write_text(json.dumps(character), encoding="utf-8")

            self.assertEqual(
                main(["analyze", str(character_path), "--output", str(analysis_path)]),
                0,
            )
            self.assertEqual(
                main(["report", str(analysis_path), "--output", str(report_path)]),
                0,
            )

            self.assertTrue(analysis_path.is_file())
            self.assertIn("Aide à la relance · CLI", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
