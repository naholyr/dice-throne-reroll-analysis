from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, combinations_with_replacement
from math import factorial

from .character import Ability, CharacterConfig
from .rules import is_success

DiceState = tuple[int, ...]

ALL_STATES: tuple[DiceState, ...] = tuple(combinations_with_replacement(range(1, 7), 5))


@dataclass(frozen=True, slots=True)
class Action:
    reroll: DiceState

    @property
    def reroll_count(self) -> int:
        return len(self.reroll)


@dataclass(frozen=True, slots=True)
class Policy:
    probability: Fraction
    whiff_probability: Fraction
    expected_additional_rolls: Fraction
    success_by_roll: tuple[Fraction, ...]
    actions: tuple[Action, ...]
    success_now: bool

    @property
    def primary_action(self) -> Action:
        if not self.actions:
            raise ValueError("Une politique terminale n'a pas d'action de relance.")
        return self.actions[0]


def state_probability(state: DiceState) -> Fraction:
    counts = Counter(state)
    permutations = factorial(5)
    for count in counts.values():
        permutations //= factorial(count)
    return Fraction(permutations, 6**5)


@lru_cache(maxsize=None)
def actions_for_state(state: DiceState) -> tuple[Action, ...]:
    actions: set[DiceState] = set()
    for count in range(1, 6):
        actions.update(combinations(state, count))
    return tuple(Action(reroll) for reroll in sorted(actions, key=lambda item: (len(item), item)))


@lru_cache(maxsize=None)
def _roll_outcomes(count: int) -> tuple[tuple[DiceState, Fraction], ...]:
    outcomes: list[tuple[DiceState, Fraction]] = []
    for rolled in combinations_with_replacement(range(1, 7), count):
        multiplicities = Counter(rolled)
        permutations = factorial(count)
        for multiplicity in multiplicities.values():
            permutations //= factorial(multiplicity)
        outcomes.append((rolled, Fraction(permutations, 6**count)))
    return tuple(outcomes)


def _kept_dice(state: DiceState, reroll: DiceState) -> DiceState:
    remaining = list(state)
    for face in reroll:
        remaining.remove(face)
    return tuple(remaining)


@lru_cache(maxsize=None)
def transitions(state: DiceState, action: Action) -> tuple[tuple[DiceState, Fraction], ...]:
    kept = _kept_dice(state, action.reroll)
    return tuple(
        (tuple(sorted((*kept, *rolled))), probability)
        for rolled, probability in _roll_outcomes(action.reroll_count)
    )


class ExactSolver:
    def __init__(self, character: CharacterConfig):
        self.character = character
        self._cache: dict[tuple[str, DiceState, int], Policy] = {}
        self._whiff_cache: dict[DiceState, bool] = {}

    def _is_whiff(self, state: DiceState) -> bool:
        cached = self._whiff_cache.get(state)
        if cached is None:
            cached = not any(
                is_success(self.character, ability, state)
                for ability in self.character.abilities
            )
            self._whiff_cache[state] = cached
        return cached

    def solve(self, ability: Ability, state: DiceState, rerolls: int) -> Policy:
        if state != tuple(sorted(state)) or len(state) != 5:
            raise ValueError("L'état doit contenir cinq faces triées.")
        if rerolls not in {0, 1, 2}:
            raise ValueError("Le nombre de relances restantes doit être 0, 1 ou 2.")
        key = (ability.identifier, state, rerolls)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        empty_timeline = tuple(Fraction(0) for _ in range(rerolls))
        if is_success(self.character, ability, state):
            result = Policy(
                Fraction(1), Fraction(0), Fraction(0), empty_timeline, (), True
            )
        elif rerolls == 0:
            result = Policy(
                Fraction(0), Fraction(self._is_whiff(state)), Fraction(0), (), (), False
            )
        else:
            result = self._best_policy(ability, state, rerolls)
        self._cache[key] = result
        return result

    def _best_policy(self, ability: Ability, state: DiceState, rerolls: int) -> Policy:
        candidates: list[
            tuple[Action, Fraction, Fraction, Fraction, tuple[Fraction, ...]]
        ] = []
        for action in actions_for_state(state):
            probability = Fraction(0)
            whiff_probability = Fraction(0)
            continuation_rolls = Fraction(0)
            success_by_roll = [Fraction(0) for _ in range(rerolls)]
            for next_state, transition_probability in transitions(state, action):
                next_policy = self.solve(ability, next_state, rerolls - 1)
                probability += transition_probability * next_policy.probability
                whiff_probability += (
                    transition_probability * next_policy.whiff_probability
                )
                continuation_rolls += (
                    transition_probability * next_policy.expected_additional_rolls
                )
                if next_policy.success_now:
                    success_by_roll[0] += transition_probability
                else:
                    for index, chance in enumerate(next_policy.success_by_roll):
                        success_by_roll[index + 1] += transition_probability * chance
            candidates.append(
                (
                    action,
                    probability,
                    whiff_probability,
                    Fraction(1) + continuation_rolls,
                    tuple(success_by_roll),
                )
            )

        best_probability = max(candidate[1] for candidate in candidates)
        probability_ties = [
            candidate for candidate in candidates if candidate[1] == best_probability
        ]
        best_whiff_probability = min(candidate[2] for candidate in probability_ties)
        whiff_ties = [
            candidate
            for candidate in probability_ties
            if candidate[2] == best_whiff_probability
        ]
        best_expected_rolls = min(candidate[3] for candidate in whiff_ties)
        ties = [
            candidate
            for candidate in whiff_ties
            if candidate[3] == best_expected_rolls
        ]
        ties.sort(key=lambda candidate: (candidate[0].reroll_count, candidate[0].reroll))
        return Policy(
            probability=best_probability,
            whiff_probability=best_whiff_probability,
            expected_additional_rolls=best_expected_rolls,
            success_by_roll=ties[0][4],
            actions=tuple(candidate[0] for candidate in ties),
            success_now=False,
        )
