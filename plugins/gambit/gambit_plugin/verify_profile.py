"""Profile verification analysis - checks if a strategy profile is a Nash equilibrium."""

from __future__ import annotations

from typing import Any

from gambit_plugin.gambit_utils import extensive_to_gambit_table, normal_form_to_gambit
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs


def run_verify_profile(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Verify if a strategy profile is a Nash equilibrium.

    Args:
        game: Deserialized game dict.
        config: Must contain 'profile' key with strategy probabilities.

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    if not config or "profile" not in config:
        raise ValueError("Profile verification requires a 'profile' in config")

    candidate_profile = config["profile"]
    format_name = game.get("format_name", "extensive")

    if format_name == "normal":
        gambit_game = normal_form_to_gambit(game)
    else:
        strategies = enumerate_strategies(game)
        gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)

    profile = gambit_game.mixed_strategy_profile()

    for player in gambit_game.players:
        player_strategies = candidate_profile.get(player.label, {})
        for strategy in player.strategies:
            prob = player_strategies.get(strategy.label, 0.0)
            profile[strategy] = prob

    profile.normalize()

    max_regret = float(profile.max_regret())
    is_equilibrium = max_regret < 1e-6

    strategy_regrets: dict[str, dict[str, float]] = {}
    for player in gambit_game.players:
        strategy_regrets[player.label] = {}
        for strategy in player.strategies:
            strategy_regrets[player.label][strategy.label] = _clean_float(
                float(profile.strategy_regret(strategy))
            )

    payoffs = {
        player.label: _clean_float(float(profile.payoff(player)))
        for player in gambit_game.players
    }

    if is_equilibrium:
        summary = "Profile is a Nash equilibrium"
    else:
        summary = f"Not an equilibrium (max regret: {max_regret:.4f})"

    return {
        "summary": summary,
        "details": {
            "is_equilibrium": is_equilibrium,
            "max_regret": _clean_float(max_regret),
            "strategy_regrets": strategy_regrets,
            "payoffs": payoffs,
        },
    }


def _clean_float(value: float, precision: int = 10) -> float:
    """Round floats to avoid floating point errors."""
    rounded = round(value, precision)
    if abs(rounded) < 1e-9:
        return 0.0
    return rounded
