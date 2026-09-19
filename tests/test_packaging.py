import tomllib
import unittest
from pathlib import Path


class PackagingTests(unittest.TestCase):
    def test_editable_install_metadata_exposes_the_documented_command(self) -> None:
        project = Path(__file__).resolve().parents[1]
        metadata = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["requires-python"], ">=3.11")
        self.assertEqual(
            metadata["project"]["scripts"]["dicethrone-helper"],
            "dicethrone_helper.cli:main",
        )
        self.assertEqual(metadata["tool"]["setuptools"]["packages"]["find"]["where"], ["src"])
        self.assertEqual(
            metadata["tool"]["setuptools"]["package-data"]["dicethrone_helper"],
            ["fonts/*.woff2", "fonts/*.txt"],
        )


if __name__ == "__main__":
    unittest.main()
