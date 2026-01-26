"""Conversion registry for game format transformations.

Provides a simple, extensible registry for converting between game representations
(e.g., extensive form <-> normal form).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Union

if TYPE_CHECKING:
    from app.models.game import ExtensiveFormGame
    from app.models.normal_form import NormalFormGame

    AnyGame = Union[ExtensiveFormGame, NormalFormGame]


@dataclass
class ConversionCheck:
    """Result of checking if a conversion is possible."""

    possible: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


@dataclass
class Conversion:
    """A registered conversion between game formats."""

    name: str
    source_format: str  # "extensive" or "normal"
    target_format: str  # "extensive" or "normal"
    can_convert: Callable[["AnyGame"], ConversionCheck]
    convert: Callable[["AnyGame"], "AnyGame"]


class ConversionRegistry:
    """Registry for game format conversions."""

    def __init__(self) -> None:
        self._conversions: dict[tuple[str, str], Conversion] = {}

    def register(self, conversion: Conversion) -> None:
        """Register a conversion."""
        key = (conversion.source_format, conversion.target_format)
        self._conversions[key] = conversion

    def check(self, game: "AnyGame", target_format: str) -> ConversionCheck:
        """Check if a game can be converted to target format."""
        from app.models.normal_form import NormalFormGame

        source_format = "normal" if isinstance(game, NormalFormGame) else "extensive"

        # Same format - no conversion needed
        if source_format == target_format:
            return ConversionCheck(possible=True, warnings=["Already in target format"])

        key = (source_format, target_format)
        conversion = self._conversions.get(key)
        if not conversion:
            return ConversionCheck(
                possible=False,
                blockers=[f"No conversion from {source_format} to {target_format}"],
            )

        return conversion.can_convert(game)

    def convert(self, game: "AnyGame", target_format: str) -> "AnyGame":
        """Convert a game to target format."""
        from app.models.normal_form import NormalFormGame

        source_format = "normal" if isinstance(game, NormalFormGame) else "extensive"

        if source_format == target_format:
            return game

        key = (source_format, target_format)
        conversion = self._conversions.get(key)
        if not conversion:
            msg = f"No conversion from {source_format} to {target_format}"
            raise ValueError(msg)

        check = conversion.can_convert(game)
        if not check.possible:
            msg = f"Cannot convert: {', '.join(check.blockers)}"
            raise ValueError(msg)

        return conversion.convert(game)

    def available_conversions(self, game: "AnyGame") -> dict[str, ConversionCheck]:
        """Get all available conversions for a game."""
        from app.models.normal_form import NormalFormGame

        source_format = "normal" if isinstance(game, NormalFormGame) else "extensive"
        results: dict[str, ConversionCheck] = {}

        for (src, tgt), conversion in self._conversions.items():
            if src == source_format:
                results[tgt] = conversion.can_convert(game)

        return results


# Global registry instance
conversion_registry = ConversionRegistry()
