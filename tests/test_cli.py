import json
import os
import tempfile
import unittest
from pathlib import Path

from dicethrone_helper.cli import main
from tests.helpers import symbol_config


class CliTests(unittest.TestCase):
    def test_extract_karnyx_skips_fresh_json_and_reextracts_after_html_change(self) -> None:
        html = """
        <html><head><title>Karnyx - Hero - Test Hero</title></head><body>
        <section wire:snapshot='{"data":{"attr":[{"offense":"8","defense":"7"}]}}'></section>
        <p>Matches</p><p>100</p><p>Win Rate</p><p>54.5%</p>
        <div data-flux-heading>Best Picks vs Test Hero</div>
        <a href="https://karnyx.app/heroes/opponent"><div><div>Opponent</div><p>60% WR</p><p>25 games</p></div></a>
        </body></html>
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "test-hero.html"
            output_dir = root / "output"
            html_path.write_text(html, encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        "extract-karnyx",
                        str(html_path),
                        "--output",
                        str(output_dir),
                    ]
                ),
                0,
            )

            output = output_dir / "test-hero.json"
            fresh_timestamp = 4_102_444_800
            os.utime(output, (fresh_timestamp, fresh_timestamp))
            self.assertEqual(
                main(
                    [
                        "extract-karnyx",
                        str(html_path),
                        "--output",
                        str(output_dir),
                        "--skip-up-to-date",
                    ]
                ),
                0,
            )
            self.assertEqual(output.stat().st_mtime, fresh_timestamp)

            os.utime(html_path, (fresh_timestamp + 1, fresh_timestamp + 1))
            self.assertEqual(
                main(
                    [
                        "extract-karnyx",
                        str(html_path),
                        "--output",
                        str(output_dir),
                        "--skip-up-to-date",
                    ]
                ),
                0,
            )
            self.assertNotEqual(output.stat().st_mtime, fresh_timestamp)

    def test_extract_karnyx_writes_hero_json(self) -> None:
        html = """
        <html><head><title>Karnyx - Hero - Test Hero</title></head><body>
        <section wire:snapshot='{"data":{"attr":[{"offense":"8","defense":"7"}]}}'></section>
        <p>Matches</p><p>100</p><p>Win Rate</p><p>54.5%</p>
        <div data-flux-heading>Best Picks vs Test Hero</div>
        <a href="https://karnyx.app/heroes/opponent"><div><div>Opponent</div><p>60% WR</p><p>25 games</p></div></a>
        <div data-flux-heading>Worst Picks vs Test Hero</div>
        </body></html>
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "test-hero.html"
            output_dir = root / "output"
            html_path.write_text(html, encoding="utf-8")

            self.assertEqual(
                main(["extract-karnyx", str(html_path), "--output", str(output_dir)]),
                0,
            )

            payload = json.loads((output_dir / "test-hero.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["hero"]["name"], "Test Hero")
            self.assertEqual(payload["attributes"], {"offense": 8, "defense": 7})
            self.assertEqual(payload["overall"], {"matches": 100, "win_rate": 54.5})
            self.assertEqual(payload["matchups"][0]["name"], "Opponent")
            self.assertEqual(payload["matchups"][0]["opponent_win_rate"], 60.0)
            self.assertEqual(payload["matchups"][0]["win_rate"], 40.0)

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
            self.assertIn('class="matchup-hero"', index)
            self.assertIn('matchups/${values.join(\'-\')}.html', index)
            self.assertNotIn('href="http', index)


if __name__ == "__main__":
    unittest.main()
