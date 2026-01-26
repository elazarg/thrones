"""Gambit-powered analysis plugins.

This sub-package contains plugins that depend on pygambit:
- Nash equilibrium computation
- IESDS (Iterated Elimination of Strictly Dominated Strategies)
- Profile verification

These plugins are only loaded when pygambit is available.
"""
from app.plugins.gambit.nash import NashEquilibriumPlugin
from app.plugins.gambit.iesds import IESDSPlugin
from app.plugins.gambit.verify_profile import VerifyProfilePlugin

__all__ = ["NashEquilibriumPlugin", "IESDSPlugin", "VerifyProfilePlugin"]
