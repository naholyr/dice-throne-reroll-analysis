from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .character import Ability, CharacterConfig


SMALL_STRAIGHTS = (frozenset((1, 2, 3, 4)), frozenset((2, 3, 4, 5)), frozenset((3, 4, 5, 6)))
LARGE_STRAIGHTS = (frozenset((1, 2, 3, 4, 5)), frozenset((2, 3, 4, 5, 6)))


def is_success(
    character: CharacterConfig, ability: Ability, dice: Sequence[int]
) -> bool:
    if len(dice) != 5 or any(face < 1 or face > 6 for face in dice):
        raise ValueError("Un lancer doit contenir cinq faces comprises entre 1 et 6.")

    if ability.kind == "symbols":
        actual = Counter(character.symbol_for_face(face) for face in dice)
        required = Counter(ability.target)
        return all(actual[symbol] >= count for symbol, count in required.items())

    faces = frozenset(dice)
    targets = SMALL_STRAIGHTS if ability.target == "small" else LARGE_STRAIGHTS
    return any(target <= faces for target in targets)
