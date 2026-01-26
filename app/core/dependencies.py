"""Centralized optional dependency checks.

This module provides a single source of truth for checking availability
of optional dependencies like pygambit.
"""
import importlib.util

# Check for pygambit availability - used by gambit-dependent plugins and formats
PYGAMBIT_AVAILABLE = importlib.util.find_spec("pygambit") is not None
