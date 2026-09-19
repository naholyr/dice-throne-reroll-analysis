from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a character file does not match the supported schema."""


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


@dataclass(frozen=True, slots=True)
class Ability:
    name: str
    kind: str
    target: str
    identifier: str

    @property
    def is_upgraded(self) -> bool:
        return self.name.endswith("*")

    @classmethod
    def from_dict(cls, raw: Any, available_symbols: frozenset[str]) -> Ability:
        if not isinstance(raw, dict):
            raise ConfigError("Chaque capacité doit être un objet JSON.")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("Chaque capacité doit avoir un nom non vide.")

        has_symbols = "symbols" in raw
        has_straight = "straight" in raw
        if has_symbols == has_straight:
            raise ConfigError(
                f"La capacité {name!r} doit définir exactement 'symbols' ou 'straight'."
            )

        if has_symbols:
            target = raw["symbols"]
            if not isinstance(target, str) or not 1 <= len(target) <= 5:
                raise ConfigError(
                    f"La combinaison de {name!r} doit contenir entre 1 et 5 symboles."
                )
            unknown = set(target) - available_symbols
            if unknown:
                raise ConfigError(
                    f"La capacité {name!r} utilise des symboles inconnus: "
                    f"{', '.join(sorted(unknown))}."
                )
            kind = "symbols"
        else:
            target = raw["straight"]
            if target not in {"small", "large"}:
                raise ConfigError(
                    f"La suite de {name!r} doit être 'small' ou 'large'."
                )
            kind = "straight"

        identifier = raw.get("id", _slugify(name))
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9-]+", identifier):
            raise ConfigError(
                f"L'identifiant de {name!r} doit utiliser a-z, 0-9 et des tirets."
            )
        return cls(name=name, kind=kind, target=target, identifier=identifier)


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    name: str
    symbols: str
    abilities: tuple[Ability, ...]
    schema_version: int = 1

    @classmethod
    def from_dict(cls, raw: Any) -> CharacterConfig:
        if not isinstance(raw, dict):
            raise ConfigError("Le fichier personnage doit contenir un objet JSON.")
        if raw.get("schema_version") != 1:
            raise ConfigError("La seule version de configuration supportée est 1.")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("Le personnage doit avoir un nom non vide.")
        symbols = raw.get("symbols")
        if not isinstance(symbols, str) or len(symbols) != 6:
            raise ConfigError("'symbols' doit contenir exactement 6 caractères.")
        if any(not symbol.isalpha() or not symbol.isupper() for symbol in symbols):
            raise ConfigError("Les symboles doivent être des lettres majuscules.")

        raw_abilities = raw.get("abilities")
        if not isinstance(raw_abilities, list) or not raw_abilities:
            raise ConfigError("Le personnage doit avoir au moins une capacité.")
        available_symbols = frozenset(symbols)
        abilities = tuple(
            Ability.from_dict(ability, available_symbols) for ability in raw_abilities
        )
        identifiers = [ability.identifier for ability in abilities]
        if len(identifiers) != len(set(identifiers)):
            raise ConfigError("Les identifiants de capacités doivent être uniques.")
        return cls(name=name, symbols=symbols, abilities=abilities)

    def symbol_for_face(self, face: int) -> str:
        if not 1 <= face <= 6:
            raise ValueError("Une face doit être comprise entre 1 et 6.")
        return self.symbols[face - 1]

    def to_dict(self) -> dict[str, Any]:
        abilities: list[dict[str, Any]] = []
        for ability in self.abilities:
            entry = {
                "id": ability.identifier,
                "name": ability.name,
                "upgraded": ability.is_upgraded,
            }
            entry[ability.kind] = ability.target
            abilities.append(entry)
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "symbols": self.symbols,
            "abilities": abilities,
        }


def load_character(path: str | Path) -> CharacterConfig:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"Impossible de lire {source}: {error}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"JSON invalide dans {source}: {error}") from error
    return CharacterConfig.from_dict(raw)
