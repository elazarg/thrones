"""Strategy enumeration and payoff resolution utilities.

This module re-exports functions from the shared strategies module.
The shared module operates on plain dicts (deserialized game JSON),
which is exactly what plugins receive.
"""
from __future__ import annotations

# Re-export from shared module for backward compatibility
from shared.strategies import (
    all_strategies as enumerate_strategies,
    iter_strategies,
    estimate_strategy_count,
    resolve_payoffs,
    resolve_payoff,
)
