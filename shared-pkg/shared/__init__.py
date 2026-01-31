"""Shared utilities used by both the core app and plugins.

This package contains code that needs to work in both contexts:
- Core app (with Pydantic models)
- Plugins (with plain dicts from JSON deserialization)

The utilities operate on plain dicts to maximize compatibility.
The core app provides wrapper functions that convert Pydantic models to dicts.
"""
from shared.efg_export import export_to_efg

__all__ = ["export_to_efg"]
