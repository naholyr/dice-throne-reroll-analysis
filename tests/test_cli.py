import json
import tempfile
import unittest
from pathlib import Path

from dicethrone_helper.cli import main
from tests.helpers import symbol_config


class CliTests(unittest.TestCase):
    def test_analyze_then_report_workflow(self) -> None:
        character = {
            "schema_version": 1,
            "name": "CLI",
            "symbols": symbol_config("AAAAAA"),
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
            self.assertIn("<title>CLI</title>", report_path.read_text(encoding="utf-8"))

    def test_index_builds_a_static_home_page_for_generated_reports(self) -> None:
        analyses = [
            {
                "schema_version": 1,
                "engine": {"name": "dicethrone-helper", "version": "test"},
                "character": {
                    "name": name,
                    "symbols": symbol_config("AAAAAA"),
                    "abilities": [{"name": "Un A", "symbols": "A"}],
                },
            }
            for name in ("Héroïne & test", "Mage")
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analysis_paths = []
            for slug, analysis in zip(("hero", "mage"), analyses, strict=True):
                path = root / f"{slug}.analysis.json"
                path.write_text(json.dumps(analysis), encoding="utf-8")
                analysis_paths.append(path)
            index_path = root / "index.html"

            self.assertEqual(
                main(
                    [
                        "index",
                        *(str(path) for path in analysis_paths),
                        "--output",
                        str(index_path),
                    ]
                ),
                0,
            )

            index = index_path.read_text(encoding="utf-8")
            self.assertIn("<title>Dice Throne Helper</title>", index)
            self.assertIn("Héroïne &amp; test", index)
            self.assertIn('href="hero.report.html"', index)
            self.assertIn('href="mage.report.html"', index)
            self.assertNotIn('href="http', index)


if __name__ == "__main__":
    unittest.main()
