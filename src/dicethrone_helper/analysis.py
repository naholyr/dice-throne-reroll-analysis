from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import __version__
from .character import Ability, CharacterConfig
from .rules import is_success
from .solver import (
    ALL_STATES,
    Action,
    DiceState,
    ExactSolver,
    Policy,
    state_probability,
    transitions,
)


def _fraction(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _kept(state: DiceState, action: Action) -> DiceState:
    kept = list(state)
    for face in action.reroll:
        kept.remove(face)
    return tuple(kept)


def _action_view(
    character: CharacterConfig, ability: Ability, state: DiceState, action: Action
) -> dict[str, Any]:
    kept_faces = _kept(state, action)
    if ability.kind == "symbols":
        keep = sorted(character.symbol_for_face(face) for face in kept_faces)
        reroll = sorted(character.symbol_for_face(face) for face in action.reroll)
        mode = "symbols"
    else:
        keep = list(kept_faces)
        reroll = list(action.reroll)
        mode = "faces"
    return {
        "mode": mode,
        "keep": keep,
        "reroll": reroll,
        "reroll_faces": list(action.reroll),
    }


def _policy_view(
    character: CharacterConfig, ability: Ability, state: DiceState, policy: Policy
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    visible_actions: set[tuple[Any, ...]] = set()
    for action in policy.actions:
        view = _action_view(character, ability, state, action)
        key = (view["mode"], tuple(view["keep"]), tuple(view["reroll"]))
        if key not in visible_actions:
            actions.append(view)
            visible_actions.add(key)
    return {
        "success_now": policy.success_now,
        "probability": _fraction(policy.probability),
        "expected_additional_rolls": _fraction(policy.expected_additional_rolls),
        "success_by_roll": [_fraction(value) for value in policy.success_by_roll],
        "actions": actions,
    }


def analyze_character(character: CharacterConfig) -> dict[str, Any]:
    solver = ExactSolver(character)
    upgraded_ability_ids = frozenset(
        ability.identifier
        for ability in character.abilities
        if ability.is_upgraded
    )
    successes_by_state = {
        state: frozenset(
            ability.identifier
            for ability in character.abilities
            if is_success(character, ability, state)
        )
        for state in ALL_STATES
    }
    standard_successes_by_state = {
        state: successes - upgraded_ability_ids
        for state, successes in successes_by_state.items()
    }
    outcome_cache: dict[
        tuple[DiceState, Action], tuple[Fraction, Fraction, dict[str, Fraction]]
    ] = {}

    def reroll_outcomes(
        target: Ability, state: DiceState, action: Action
    ) -> dict[str, Any]:
        key = (state, action)
        cached = outcome_cache.get(key)
        if cached is None:
            nothing = Fraction(0)
            nothing_without_upgraded_abilities = Fraction(0)
            probabilities = {
                ability.identifier: Fraction(0) for ability in character.abilities
            }
            for next_state, transition_probability in transitions(state, action):
                successes = successes_by_state[next_state]
                if not successes:
                    nothing += transition_probability
                if not standard_successes_by_state[next_state]:
                    nothing_without_upgraded_abilities += transition_probability
                for ability_id in successes:
                    probabilities[ability_id] += transition_probability
            cached = (
                nothing,
                nothing_without_upgraded_abilities,
                probabilities,
            )
            outcome_cache[key] = cached
        nothing, nothing_without_upgraded_abilities, probabilities = cached
        return {
            "nothing": _fraction(nothing),
            "nothing_without_upgraded_abilities": _fraction(
                nothing_without_upgraded_abilities
            ),
            "accidental_abilities": [
                {
                    "ability_id": ability.identifier,
                    "probability": _fraction(probabilities[ability.identifier]),
                }
                for ability in character.abilities
                if ability.identifier != target.identifier
                and probabilities[ability.identifier] > 0
            ],
        }

    def second_roll_policy_view(
        ability: Ability, state: DiceState, policy: Policy
    ) -> dict[str, Any]:
        view = _policy_view(character, ability, state, policy)
        if policy.actions:
            view["reroll_outcomes"] = reroll_outcomes(
                ability, state, policy.primary_action
            )
        return view

    states: list[dict[str, Any]] = []
    for state in ALL_STATES:
        states.append(
            {
                "dice": list(state),
                "initial_probability": _fraction(state_probability(state)),
                "after_first_roll": {
                    ability.identifier: _policy_view(
                        character, ability, state, solver.solve(ability, state, 2)
                    )
                    for ability in character.abilities
                },
                "after_second_roll": {
                    ability.identifier: second_roll_policy_view(
                        ability, state, solver.solve(ability, state, 1)
                    )
                    for ability in character.abilities
                },
            }
        )

    global_results: list[dict[str, Any]] = []
    for ability in character.abilities:
        probability = Fraction(0)
        expected_rolls = Fraction(1)
        success_by_roll = [Fraction(0), Fraction(0), Fraction(0)]
        for state in ALL_STATES:
            initial_probability = state_probability(state)
            policy = solver.solve(ability, state, 2)
            probability += initial_probability * policy.probability
            expected_rolls += initial_probability * policy.expected_additional_rolls
            if is_success(character, ability, state):
                success_by_roll[0] += initial_probability
            else:
                for index, chance in enumerate(policy.success_by_roll):
                    success_by_roll[index + 1] += initial_probability * chance
        global_results.append(
            {
                "ability_id": ability.identifier,
                "probability": _fraction(probability),
                "expected_rolls": _fraction(expected_rolls),
                "success_by_roll": [_fraction(value) for value in success_by_roll],
            }
        )

    return {
        "schema_version": 1,
        "engine": {"name": "dicethrone-helper", "version": __version__},
        "character": character.to_dict(),
        "rules": {
            "dice_count": 5,
            "face_count": 6,
            "maximum_rolls": 3,
            "state_ordering": "sorted",
            "probabilities": "exact_fractions",
        },
        "global": global_results,
        "states": states,
    }


def write_analysis(analysis: dict[str, Any], destination: str | Path) -> None:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
