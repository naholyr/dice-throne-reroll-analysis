from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class KarnyxExtractionError(ValueError):
    """Raised when a downloaded Karnyx page does not contain expected data."""


_MATCHUP_RE = re.compile(
    r"^(?P<name>.+?)\s+(?P<win_rate>\d+(?:\.\d+)?)%\s+WR\s+"
    r"(?P<matches>\d+)\s+games$"
)
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._elements: list[dict[str, Any]] = []
        self._matchup_section: str | None = None
        self.attributes: dict[str, int] | None = None
        self.paragraphs: list[str] = []
        self.matchups: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in _VOID_TAGS:
            return
        self._elements.append({"tag": tag, "attrs": attributes, "text": []})
        snapshot = attributes.get("wire:snapshot")
        if snapshot and '"attr"' in snapshot:
            try:
                payload = json.loads(snapshot)
                values = payload["data"]["attr"][0]
                self.attributes = {name: int(value) for name, value in values.items()}
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        for element in self._elements:
            element["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._elements:
            return
        element = self._elements.pop()
        if element["tag"] != tag:
            return
        text = " ".join(element["text"]).strip()
        if tag == "p":
            self.paragraphs.append(text)
        if tag == "div" and "data-flux-heading" in element["attrs"]:
            if text.startswith("Best Picks vs "):
                self._matchup_section = "best"
            elif text.startswith("Worst Picks vs "):
                self._matchup_section = "worst"
        if tag == "a" and self._matchup_section == "best":
            href = element["attrs"].get("href", "")
            match = _MATCHUP_RE.fullmatch(text)
            if href.startswith("https://karnyx.app/heroes/") and match:
                self.matchups.append(
                    {
                        "name": match["name"],
                        "slug": href.rsplit("/", 1)[-1],
                        "win_rate": 100 - float(match["win_rate"]),
                        "opponent_win_rate": float(match["win_rate"]),
                        "matches": int(match["matches"]),
                    }
                )


def extract_html(html: str, source_file: str | None = None) -> dict[str, Any]:
    parser = _PageParser()
    parser.feed(html)
    title_match = re.search(r"<title>\s*Karnyx - Hero - (.+?)\s*</title>", html)
    if not title_match:
        raise KarnyxExtractionError("Nom du héros introuvable")
    if parser.attributes is None:
        raise KarnyxExtractionError("Attributs introuvables")
    if not parser.matchups:
        raise KarnyxExtractionError("Matchups introuvables dans Best Picks")

    def stat(label: str) -> float | int:
        try:
            index = parser.paragraphs.index(label)
            value = parser.paragraphs[index + 1].replace(",", "")
            return float(value[:-1]) if value.endswith("%") else int(value)
        except (ValueError, IndexError) as error:
            raise KarnyxExtractionError(f"Statistique globale introuvable: {label}") from error

    name = title_match.group(1)
    return {
        "schema_version": 1,
        "source_file": source_file,
        "hero": {"name": name},
        "attributes": parser.attributes,
        "overall": {"matches": stat("Matches"), "win_rate": stat("Win Rate")},
        "matchups": parser.matchups,
    }


def extract_file(path: Path) -> dict[str, Any]:
    return extract_html(path.read_text(encoding="utf-8"), path.name)


def _is_extraction_up_to_date(source: Path, output: Path) -> bool:
    return output.is_file() and source.stat().st_mtime < output.stat().st_mtime


def write_extractions(
    paths: list[Path],
    output_dir: Path,
    *,
    skip_if_up_to_date: bool = False,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for path in paths:
        output = output_dir / f"{path.stem}.json"
        if not skip_if_up_to_date or not _is_extraction_up_to_date(path, output):
            output.write_text(
                json.dumps(extract_file(path), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        outputs.append(output)
    return outputs