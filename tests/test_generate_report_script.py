import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


class GenerateReportScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary_directory.name)
        (self.project / "characters").mkdir()
        (self.project / "build").mkdir()
        (self.project / "generated-website").mkdir()
        (self.project / "src").mkdir()
        (self.project / ".venv" / "bin").mkdir(parents=True)
        (self.project / "bin").mkdir()
        (self.project / "characters" / "hero.json").write_text("{}\n", encoding="utf-8")
        (self.project / "characters" / "mage.json").write_text("{}\n", encoding="utf-8")
        (self.project / "src" / "engine.py").write_text("# engine\n", encoding="utf-8")

        source_script = Path(__file__).resolve().parents[1] / "generate-report.sh"
        shutil.copy2(source_script, self.project / "generate-report.sh")

        helper = self.project / ".venv" / "bin" / "dicethrone-helper"
        helper.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$1" >> "$HELPER_CALLS"
while (( $# )); do
  if [[ "$1" == "--output" ]]; then
    mkdir -p "$(dirname "$2")"
    : > "$2"
    exit 0
  fi
  shift
done
exit 2
""",
            encoding="utf-8",
        )
        helper.chmod(0o755)

        opener = self.project / "bin" / "open"
        opener.write_text(
            "#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >> \"$OPEN_CALLS\"\n",
            encoding="utf-8",
        )
        opener.chmod(0o755)

        self.helper_calls = self.project / "helper.calls"
        self.open_calls = self.project / "open.calls"
        self.environment = {
            **os.environ,
            "PATH": f"{self.project / 'bin'}:{os.environ['PATH']}",
            "HELPER_CALLS": str(self.helper_calls),
            "OPEN_CALLS": str(self.open_calls),
        }

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_script(self, *arguments: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.project / "generate-report.sh"), *arguments],
            cwd=self.project,
            env=self.environment,
            input=input_text,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_named_character_reuses_fresh_analysis_and_always_rebuilds_report(self) -> None:
        self.run_script("hero")

        self.assertEqual(self.helper_calls.read_text().splitlines(), ["analyze", "report"])
        self.assertEqual(
            self.open_calls.read_text().splitlines(),
            [str(self.project / "build" / "hero.report.html")],
        )

        self.run_script("hero")

        self.assertEqual(
            self.helper_calls.read_text().splitlines(),
            ["analyze", "report", "report"],
        )

        future = time.time() + 2
        os.utime(self.project / "characters" / "hero.json", (future, future))
        self.run_script("hero")

        self.assertEqual(
            self.helper_calls.read_text().splitlines(),
            ["analyze", "report", "report", "analyze", "report"],
        )

    def test_missing_character_argument_supports_arrow_key_selection(self) -> None:
        result = self.run_script(input_text="\x1b[B\n")

        self.assertIn("↑/↓", result.stderr + result.stdout)
        self.assertEqual(self.helper_calls.read_text().splitlines(), ["analyze", "report"])
        self.assertEqual(
            self.open_calls.read_text().splitlines(),
            [str(self.project / "build" / "mage.report.html")],
        )

    def test_named_character_rebuilds_analysis_after_engine_change(self) -> None:
        self.run_script("hero")

        future = time.time() + 2
        os.utime(self.project / "src" / "engine.py", (future, future))
        self.run_script("hero")

        self.assertEqual(
            self.helper_calls.read_text().splitlines(),
            ["analyze", "report", "analyze", "report"],
        )

    def test_all_generates_every_report_and_opens_the_site_index(self) -> None:
        self.run_script("--all")

        self.assertEqual(
            self.helper_calls.read_text().splitlines(),
            ["analyze", "report", "analyze", "report", "index"],
        )
        self.assertEqual(
            self.open_calls.read_text().splitlines(),
            [str(self.project / "build" / "index.html")],
        )


if __name__ == "__main__":
    unittest.main()
