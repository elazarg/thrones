"""Game format conversion system.

Provides conversions between game representations (e.g., EFG <-> NFG).
"""

# Import converters for registration side effects
from app.conversions import efg_nfg as _efg_nfg  # noqa: F401
from app.conversions.registry import (
    Conversion,
    ConversionCheck,
    ConversionRegistry,
)

__all__ = [
    "Conversion",
    "ConversionCheck",
    "ConversionRegistry",
]
