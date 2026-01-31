"""Replicator dynamics analysis for normal-form games."""

from __future__ import annotations

from typing import Any

import numpy as np


def nfg_to_payoff_matrix(game: dict[str, Any]) -> np.ndarray:
    """Convert NFG JSON to NumPy payoff matrix.

    For 2-player symmetric games, EGTTools expects just player 1's payoffs.
    For asymmetric games, we return the full payoff structure.

    Args:
        game: Deserialized NFG game dict with 'payoffs' key.

    Returns:
        NumPy array of payoffs.
    """
    payoffs = game.get("payoffs", [])
    if not payoffs:
        raise ValueError("Game has no payoffs defined")

    # payoffs[row][col] = [p1_payoff, p2_payoff, ...]
    # For symmetric games, we just need player 1's payoff matrix
    return np.array([[cell[0] for cell in row] for row in payoffs], dtype=float)


def run_replicator_dynamics(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Simulate replicator dynamics for a normal-form game.

    Replicator dynamics models strategy evolution in infinite populations
    where strategies that perform above average grow in frequency.

    Uses pure numpy implementation of the replicator equation:
        dx_i/dt = x_i * (f_i - avg_fitness)

    Args:
        game: Deserialized NFG game dict.
        config: Configuration with optional keys:
            - time_steps: Number of simulation steps (default: 100)
            - initial_population: Initial strategy frequencies (default: uniform)
            - dt: Time step size (default: 0.01)

    Returns:
        Dict with 'summary' and 'details' keys containing trajectory data.
    """
    config = config or {}
    time_steps = config.get("time_steps", 100)
    dt = config.get("dt", 0.01)

    # Get payoff matrix
    payoff_matrix = nfg_to_payoff_matrix(game)
    n_rows, n_cols = payoff_matrix.shape

    # Replicator dynamics requires symmetric games (same strategies for both players)
    if n_rows != n_cols:
        raise ValueError(
            f"Replicator dynamics requires a symmetric game (square payoff matrix). "
            f"Got {n_rows}x{n_cols} matrix. Both players must have the same number of strategies."
        )

    n_strategies = n_rows

    # Initial population frequencies
    initial_pop = config.get("initial_population")
    if initial_pop is None:
        # Default to uniform distribution
        x0 = np.ones(n_strategies) / n_strategies
    else:
        x0 = np.array(initial_pop, dtype=float)
        if len(x0) != n_strategies:
            raise ValueError(
                f"Initial population size {len(x0)} doesn't match "
                f"number of strategies {n_strategies}"
            )
        # Normalize to ensure it sums to 1
        x0 = x0 / x0.sum()

    # Get strategy labels from NFG format
    # NFG has strategies as tuple[list[str], list[str]] at top level
    strategies_tuple = game.get("strategies", [])
    if strategies_tuple and len(strategies_tuple) > 0:
        # Use player 1's strategies (row player) for symmetric analysis
        strategy_labels = list(strategies_tuple[0]) if strategies_tuple[0] else []
        if len(strategy_labels) != n_strategies:
            strategy_labels = [f"Strategy {i}" for i in range(n_strategies)]
    else:
        strategy_labels = [f"Strategy {i}" for i in range(n_strategies)]

    # Simulate replicator dynamics
    trajectory = []
    x = x0.copy()
    times = []

    for t in range(time_steps + 1):
        trajectory.append(x.copy().tolist())
        times.append(t * dt)

        if t < time_steps:
            # Compute fitness for each strategy
            fitness = payoff_matrix @ x
            avg_fitness = np.dot(x, fitness)

            # Replicator equation: dx_i/dt = x_i * (f_i - avg_f)
            dx = x * (fitness - avg_fitness)
            x = x + dt * dx

            # Ensure valid probabilities
            x = np.maximum(x, 0)
            x = x / x.sum()

    # Find equilibrium strategies (those with significant frequency at end)
    final_state = trajectory[-1]
    dominant_strategies = [
        strategy_labels[i] for i, freq in enumerate(final_state) if freq > 0.01
    ]

    if len(dominant_strategies) == 1:
        summary = f"Converges to {dominant_strategies[0]}"
    elif len(dominant_strategies) == n_strategies:
        summary = "Mixed equilibrium reached"
    else:
        summary = f"Partial equilibrium: {', '.join(dominant_strategies)}"

    return {
        "summary": summary,
        "details": {
            "trajectory": trajectory,
            "times": times,
            "strategy_labels": strategy_labels,
            "initial_state": x0.tolist(),
            "final_state": final_state,
            "time_steps": time_steps,
            "dt": dt,
        },
    }
