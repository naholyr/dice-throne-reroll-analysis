import json
import os
import tempfile
import unittest
from pathlib import Path

from dicethrone_helper.matchup_report import (
    calculate_matchup_report,
    write_all_matchup_reports,
    write_matchup_report,
)


def hero_payload(slug: str, name: str, rates: dict[str, float]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source_file": f"{slug}.html",
        "hero": {"name": name},
        "attributes": {},
        "overall": {"matches": 100, "win_rate": 50},
        "matchups": [
            {
                "name": opponent.title(),
                "slug": opponent,
                "win_rate": rate,
                "opponent_win_rate": 100 - rate,
                "matches": 100,
            }
            for opponent, rate in rates.items()
        ],
    }


class MatchupReportTests(unittest.TestCase):
    def test_identifies_shared_nemeses_and_sweets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            heroes_dir = Path(directory)
            payloads = {
                "alpha": hero_payload("alpha", "Alpha", {"beta": 50, "nemesis": 40, "sweet": 60}),
                "beta": hero_payload("beta", "Beta", {"alpha": 50, "nemesis": 42, "sweet": 58}),
                "gamma": hero_payload("gamma", "Gamma", {"alpha": 50, "beta": 50, "nemesis": 60, "sweet": 40}),
            }
            for slug, payload in payloads.items():
                (heroes_dir / f"{slug}.json").write_text(json.dumps(payload), encoding="utf-8")

            report = calculate_matchup_report(["gamma", "alpha", "beta"], heroes_dir)

            nemesis = next(item for item in report["matchups"] if item["slug"] == "nemesis")
            sweet = next(item for item in report["matchups"] if item["slug"] == "sweet")
            self.assertEqual(nemesis["nemesis_count"], 2)
            self.assertEqual(nemesis["best"]["hero"], "Gamma")
            self.assertEqual(sweet["sweet_count"], 2)
            self.assertEqual({item["slug"] for item in report["team"]}, {"alpha", "beta", "gamma"})
            self.assertNotIn("alpha", {item["slug"] for item in report["matchups"]})

    def test_writes_alphabetically_sorted_self_contained_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            heroes_dir = root / "heroes"
            output_dir = root / "reports"
            heroes_dir.mkdir()
            for slug in ("alpha", "beta", "gamma"):
                payload = hero_payload(
                    slug,
                    slug.title(),
                    {other: 50 for other in ("alpha", "beta", "gamma", "opponent") if other != slug},
                )
                (heroes_dir / f"{slug}.json").write_text(json.dumps(payload), encoding="utf-8")

            output = write_matchup_report(["gamma", "alpha", "beta"], heroes_dir, output_dir)

            self.assertEqual(output.name, "alpha-beta-gamma.html")
            contents = output.read_text(encoding="utf-8")
            self.assertIn("<title>Matchups - Gamma / Alpha / Beta</title>", contents)
            self.assertIn("@font-face{font-family:\"League Spartan\"", contents)
            self.assertNotIn('src="http', contents)

    def test_writes_one_report_for_each_three_hero_combination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            heroes_dir = root / "heroes"
            output_dir = root / "reports"
            heroes_dir.mkdir()
            slugs = ("alpha", "beta", "gamma", "delta")
            for slug in slugs:
                payload = hero_payload(
                    slug,
                    slug.title(),
                    {other: 50 for other in slugs if other != slug},
                )
                (heroes_dir / f"{slug}.json").write_text(json.dumps(payload), encoding="utf-8")

            outputs = write_all_matchup_reports(heroes_dir, output_dir)

            self.assertEqual(len(outputs), 4)
            self.assertEqual(
                {output.name for output in outputs},
                {
                    "alpha-beta-delta.html",
                    "alpha-beta-gamma.html",
                    "alpha-delta-gamma.html",
                    "beta-delta-gamma.html",
                },
            )

    def test_skips_fresh_report_and_rebuilds_after_source_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            heroes_dir = root / "heroes"
            output_dir = root / "reports"
            heroes_dir.mkdir()
            for slug in ("alpha", "beta", "gamma"):
                payload = hero_payload(
                    slug,
                    slug.title(),
                    {other: 50 for other in ("alpha", "beta", "gamma", "opponent") if other != slug},
                )
                (heroes_dir / f"{slug}.json").write_text(json.dumps(payload), encoding="utf-8")

            output = write_matchup_report(["alpha", "beta", "gamma"], heroes_dir, output_dir)
            fresh_timestamp = 4_102_444_800
            os.utime(output, (fresh_timestamp, fresh_timestamp))
            write_matchup_report(
                ["alpha", "beta", "gamma"],
                heroes_dir,
                output_dir,
                skip_if_up_to_date=True,
            )
            self.assertEqual(output.stat().st_mtime, fresh_timestamp)

            changed_timestamp = fresh_timestamp + 1
            os.utime(heroes_dir / "beta.json", (changed_timestamp, changed_timestamp))
            write_matchup_report(
                ["alpha", "beta", "gamma"],
                heroes_dir,
                output_dir,
                skip_if_up_to_date=True,
            )
            self.assertNotEqual(output.stat().st_mtime, fresh_timestamp)


if __name__ == "__main__":
    unittest.main()