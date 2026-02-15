"""Conversion registry for game format transformations.

Provides a simple, extensible registry for converting between game representations
(e.g., extensive form <-> normal form).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import AnyGame


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
    can_convert: Callable[[AnyGame], ConversionCheck]
    convert: Callable[[AnyGame], AnyGame]


class ConversionRegistry:
    """Registry for game format conversions."""

    def __init__(self) -> None:
        self._conversions: dict[tuple[str, str], Conversion] = {}

    def register(self, conversion: Conversion) -> None:
        """Register a conversion."""
        key = (conversion.source_format, conversion.target_format)
        self._conversions[key] = conversion

    def _find_conversion_path(
        self, source_format: str, target_format: str
    ) -> list[tuple[str, str]] | None:
        """Find shortest conversion path using BFS.

        Returns list of (source, target) edge tuples representing the path,
        or None if no path exists.
        """
        if source_format == target_format:
            return []

        # Build adjacency list from registered conversions
        neighbors: dict[str, list[str]] = {}
        for src, tgt in self._conversions:
            neighbors.setdefault(src, []).append(tgt)

        # BFS to find shortest path
        queue: deque[tuple[str, list[tuple[str, str]]]] = deque([(source_format, [])])
        visited = {source_format}

        while queue:
            current, path = queue.popleft()
            for next_fmt in neighbors.get(current, []):
                edge = (current, next_fmt)
                new_path = path + [edge]
                if next_fmt == target_format:
                    return new_path
                if next_fmt not in visited:
                    visited.add(next_fmt)
                    queue.append((next_fmt, new_path))

        return None

    def check(self, game: AnyGame, target_format: str, *, quick: bool = False) -> ConversionCheck:
        """Check if a game can be converted to target format.

        Supports chained conversions (e.g., MAID → EFG → NFG).

        Args:
            game: The game to convert.
            target_format: Target format name.
            quick: If True, only check if path exists without performing
                   intermediate conversions. Faster but less accurate for
                   multi-hop paths.
        """
        source_format = game.format_name

        # Same format - no conversion needed
        if source_format == target_format:
            return ConversionCheck(possible=True, warnings=["Already in target format"])

        path = self._find_conversion_path(source_format, target_format)
        if not path:
            return ConversionCheck(
                possible=False,
                blockers=[f"No conversion path from {source_format} to {target_format}"],
            )

        # Quick check: only verify path exists and first step is possible
        if quick:
            first_conv = self._conversions[path[0]]
            check_result = first_conv.can_convert(game)
            if not check_result.possible:
                return check_result
            warnings = check_result.warnings.copy()
            if len(path) > 1:
                warnings.insert(0, f"Requires {len(path)}-step conversion")
            return ConversionCheck(possible=True, warnings=warnings)

        # Full check: verify each step, performing intermediate conversions
        all_warnings: list[str] = []
        current_game = game

        for i, (src, tgt) in enumerate(path):
            conversion = self._conversions[(src, tgt)]
            check_result = conversion.can_convert(current_game)

            if not check_result.possible:
                return ConversionCheck(
                    possible=False,
                    blockers=check_result.blockers,
                    warnings=all_warnings,
                )

            all_warnings.extend(check_result.warnings)

            # For subsequent steps, we need to do the actual conversion to check further
            if i < len(path) - 1:
                try:
                    current_game = conversion.convert(current_game)
                except Exception as e:
                    return ConversionCheck(
                        possible=False,
                        blockers=[f"Intermediate conversion failed: {e}"],
                        warnings=all_warnings,
                    )

        if len(path) > 1:
            all_warnings.insert(0, f"Requires {len(path)}-step conversion")

        return ConversionCheck(possible=True, warnings=all_warnings)

    def convert(self, game: AnyGame, target_format: str) -> AnyGame:
        """Convert a game to target format.

        Supports chained conversions (e.g., MAID → EFG → NFG).
        """
        source_format = game.format_name

        if source_format == target_format:
            return game

        path = self._find_conversion_path(source_format, target_format)
        if not path:
            msg = f"No conversion path from {source_format} to {target_format}"
            raise ValueError(msg)

        # Apply each conversion in the path
        current_game = game
        for src, tgt in path:
            conversion = self._conversions[(src, tgt)]
            check_result = conversion.can_convert(current_game)

            if not check_result.possible:
                msg = f"Cannot convert {src} to {tgt}: {', '.join(check_result.blockers)}"
                raise ValueError(msg)

            current_game = conversion.convert(current_game)

        return current_game

    def available_conversions(
        self, game: AnyGame, *, quick: bool = True
    ) -> dict[str, ConversionCheck]:
        """Get all available conversions for a game.

        Includes both direct and chained conversions.

        Args:
            game: The game to check conversions for.
            quick: If True (default), uses quick checks that don't perform
                   intermediate conversions. Faster but may not catch all
                   blockers for multi-hop paths.
        """
        source_format = game.format_name
        results: dict[str, ConversionCheck] = {}

        # Collect all possible target formats
        all_targets: set[str] = set()
        for src, tgt in self._conversions.keys():
            all_targets.add(tgt)
            all_targets.add(src)

        # Check each potential target
        for target in all_targets:
            if target == source_format:
                continue
            check_result = self.check(game, target, quick=quick)
            # Only include if possible or has a path (even if blocked)
            if check_result.possible or self._find_conversion_path(source_format, target):
                results[target] = check_result

        return results
