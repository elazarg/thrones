"""Gambit format parsers.

This sub-package contains parsers for Gambit file formats (.efg, .nfg)
that depend on pygambit. These parsers are only loaded when pygambit is available.
"""
from app.formats.gambit.efg import parse_efg
from app.formats.gambit.nfg import parse_nfg

__all__ = ["parse_efg", "parse_nfg"]
