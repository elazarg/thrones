"""Game format conversion system.

Provides conversions between game representations (e.g., EFG <-> NFG).
"""
from app.conversions.registry import (
    Conversion,
    ConversionCheck,
    ConversionRegistry,
)

# Import converters for registration side effects
from app.conversions import efg_nfg as _efg_nfg  # noqa: F401

__all__ = [
    "Conversion",
    "ConversionCheck",
    "ConversionRegistry",
]
