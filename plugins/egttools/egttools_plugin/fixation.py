"""Fixation probability and evolutionary stability analysis."""
from __future__ import annotations

from typing import Any

import numpy as np


def nfg_to_payoff_matrix(game: dict[str, Any]) -> np.ndarray:
    """Convert NFG JSON to NumPy payoff matrix."""
    payoffs = game.get("payoffs", [])
    if not payoffs:
        raise ValueError("Game has no payoffs defined")
    return np.array([[cell[0] for cell in row] for row in payoffs], dtype=float)


def run_evolutionary_stability(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Analyze evolutionary stability using finite population dynamics.

    Computes fixation probabilities and stationary distribution for
    strategies in a finite population using the Moran process.

    Uses pure numpy implementation of:
    - Moran process fixation probabilities: rho = (1 - exp(-s)) / (1 - exp(-N*s))
    - Stationary distribution via eigenvalue decomposition

    Args:
        game: Deserialized NFG game dict.
        config: Configuration with optional keys:
            - population_size: Population size Z (default: 100)
            - mutation_rate: Mutation rate mu (default: 0.001)
            - intensity_of_selection: Selection strength beta (default: 1.0)

    Returns:
        Dict with 'summary' and 'details' containing stability analysis.
    """
    config = config or {}
    pop_size = config.get("population_size", 100)
    mutation_rate = config.get("mutation_rate", 0.001)
    beta = config.get("intensity_of_selection", 1.0)

    try:
        payoff_matrix = nfg_to_payoff_matrix(game)
    except ValueError as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }

    n_rows, n_cols = payoff_matrix.shape

    # Evolutionary stability analysis requires symmetric games
    if n_rows != n_cols:
        raise ValueError(
            f"Evolutionary stability requires a symmetric game (square payoff matrix). "
            f"Got {n_rows}x{n_cols} matrix. Both players must have the same number of strategies."
        )

    n_strategies = n_rows

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

    try:
        # Compute fixation probabilities using analytical methods
        # This computes probability that a single mutant of type j
        # takes over a population of type i
        fixation_probs = np.zeros((n_strategies, n_strategies))

        for i in range(n_strategies):
            for j in range(n_strategies):
                if i == j:
                    fixation_probs[i, j] = 0.0
                else:
                    # Use Moran process fixation probability
                    # For neutral drift, fixation prob = 1/N
                    # With selection, it depends on fitness differences
                    try:
                        # Compute average payoffs in monomorphic populations
                        payoff_resident = payoff_matrix[i, i]
                        payoff_mutant_vs_resident = payoff_matrix[j, i]

                        # Selection coefficient
                        s = beta * (payoff_mutant_vs_resident - payoff_resident)

                        if abs(s) < 1e-10:
                            # Neutral: fixation = 1/N
                            fixation_probs[i, j] = 1.0 / pop_size
                        else:
                            # Moran process fixation probability formula
                            # rho = (1 - exp(-s)) / (1 - exp(-N*s))
                            if s > 0:
                                fixation_probs[i, j] = (1 - np.exp(-s)) / (
                                    1 - np.exp(-pop_size * s)
                                )
                            else:
                                fixation_probs[i, j] = (1 - np.exp(-s)) / (
                                    1 - np.exp(-pop_size * s)
                                )
                    except Exception:
                        fixation_probs[i, j] = 1.0 / pop_size

        # Compute transition matrix for small mutation limit
        # T[i,j] = fixation_prob[i,j] for i != j, normalized
        transition_matrix = fixation_probs.copy()
        for i in range(n_strategies):
            row_sum = transition_matrix[i].sum()
            if row_sum > 0:
                transition_matrix[i] /= row_sum
            transition_matrix[i, i] = 0
            transition_matrix[i, i] = 1 - transition_matrix[i].sum()

        # Compute stationary distribution
        # Find eigenvector with eigenvalue 1
        eigenvalues, eigenvectors = np.linalg.eig(transition_matrix.T)
        idx = np.argmin(np.abs(eigenvalues - 1))
        stationary = np.real(eigenvectors[:, idx])
        stationary = np.abs(stationary)
        stationary = stationary / stationary.sum()

        # Identify dominant strategy
        dominant_idx = np.argmax(stationary)
        dominant_strategy = strategy_labels[dominant_idx]
        dominant_freq = stationary[dominant_idx]

        if dominant_freq > 0.9:
            summary = f"{dominant_strategy} dominates ({dominant_freq:.1%})"
        elif dominant_freq > 0.5:
            summary = f"{dominant_strategy} prevails ({dominant_freq:.1%})"
        else:
            summary = "Mixed evolutionary stable state"

        return {
            "summary": summary,
            "details": {
                "stationary_distribution": {
                    label: float(freq)
                    for label, freq in zip(strategy_labels, stationary)
                },
                "fixation_probabilities": {
                    f"{strategy_labels[i]}_invades_{strategy_labels[j]}": float(
                        fixation_probs[j, i]
                    )
                    for i in range(n_strategies)
                    for j in range(n_strategies)
                    if i != j
                },
                "population_size": pop_size,
                "mutation_rate": mutation_rate,
                "intensity_of_selection": beta,
                "strategy_labels": strategy_labels,
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }
