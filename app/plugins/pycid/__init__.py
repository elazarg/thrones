"""PyCID-powered analysis plugins.

This sub-package contains plugins that depend on pycid:
- Nash equilibrium computation for MAIDs

These plugins are only loaded when pycid is available.
"""
from app.plugins.pycid.nash import MAIDNashEquilibriumPlugin

__all__ = ["MAIDNashEquilibriumPlugin"]
