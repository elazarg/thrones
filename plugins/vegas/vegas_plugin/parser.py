"""Parse and compile .vg files using the Vegas JAR."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to Vegas JAR - relative to this file's location
VEGAS_JAR = Path(__file__).parent.parent / "lib" / "vegas.jar"


def _extract_title_from_source(content: str, filename: str) -> str:
    """Extract a title from Vegas source code or filename."""
    # Try to find game name from 'game main()' or 'game GameName()'
    match = re.search(r"game\s+(\w+)\s*\(", content)
    if match and match.group(1) != "main":
        return match.group(1)
    # Fall back to filename without extension
    return Path(filename).stem


def _extract_players_from_source(content: str) -> list[str]:
    """Extract player names from Vegas source code.

    Looks for 'join Player()' patterns.
    """
    players = []
    for match in re.finditer(r"join\s+(\w+)\s*\(\s*\)", content):
        players.append(match.group(1))
    return players


def parse_vg(content: str, filename: str = "game.vg") -> dict[str, Any]:
    """Parse a .vg file and return a VegasGame dict.

    This is a quick parse that just wraps the source code.
    Actual compilation to MAID happens via the conversion endpoint.

    Args:
        content: The .vg file content
        filename: Original filename (used for naming)

    Returns:
        Dict matching VegasGame schema
    """
    title = _extract_title_from_source(content, filename)
    players = _extract_players_from_source(content)

    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": f"Vegas game from {filename}",
        "source_code": content,
        "players": players,
        "tags": ["vegas"],
        "format_name": "vegas",
    }


def compile_to_maid(content: str, filename: str = "game.vg") -> dict[str, Any]:
    """Compile a .vg file to MAID format using the Vegas JAR.

    1. Write content to temp file
    2. Invoke Vegas JAR with --maid flag
    3. Read generated .maid.json file
    4. Return the parsed MAID dict

    Args:
        content: The .vg file content
        filename: Original filename (used for naming)

    Returns:
        Dict matching MAIDGame schema

    Raises:
        ValueError: If compilation fails
        FileNotFoundError: If Vegas JAR is not found
    """
    if not VEGAS_JAR.exists():
        raise FileNotFoundError(f"Vegas JAR not found at {VEGAS_JAR}")

    # Ensure filename ends with .vg
    if not filename.endswith(".vg"):
        filename = filename + ".vg"

    with tempfile.TemporaryDirectory() as tmpdir:
        vg_path = Path(tmpdir) / filename
        vg_path.write_text(content, encoding="utf-8")

        logger.info("Running Vegas compiler on %s", vg_path)

        # Run Vegas to generate MAID JSON
        result = subprocess.run(
            ["java", "-jar", str(VEGAS_JAR), str(vg_path), "--maid"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = (
                result.stderr.strip() or result.stdout.strip() or "Unknown error"
            )
            logger.error("Vegas compilation failed: %s", error_msg)
            raise ValueError(f"Vegas compilation failed: {error_msg}")

        # Read the generated MAID JSON file
        base_name = filename.removesuffix(".vg")
        maid_path = Path(tmpdir) / f"{base_name}.maid.json"

        if not maid_path.exists():
            raise ValueError("Vegas did not produce MAID output. Check the Vegas log.")

        maid_content = maid_path.read_text(encoding="utf-8")
        game = json.loads(maid_content)

        logger.info("Successfully compiled %s to MAID", filename)
        return game


# Compile target definitions
COMPILE_TARGETS = {
    "solidity": {
        "id": "solidity",
        "type": "code",
        "language": "solidity",
        "label": "Solidity Smart Contract",
        "flag": "--sol",
        "extension": ".sol",
    },
    "vyper": {
        "id": "vyper",
        "type": "code",
        "language": "vyper",
        "label": "Vyper Smart Contract",
        "flag": "--vyper",
        "extension": ".vy",
    },
    "smt": {
        "id": "smt",
        "type": "code",
        "language": "smt-lib",
        "label": "SMT-LIB (Z3)",
        "flag": "--z3",
        "extension": ".z3",
    },
    "scribble": {
        "id": "scribble",
        "type": "code",
        "language": "scribble",
        "label": "Scribble Protocol",
        "flag": "--scr",
        "extension": ".scr",
    },
}


def compile_to_target(
    content: str, target: str, filename: str = "game.vg"
) -> dict[str, Any]:
    """Compile a .vg file to a specific target format.

    Args:
        content: The .vg file content
        target: Target ID (solidity, vyper, smt, scribble)
        filename: Original filename (used for naming)

    Returns:
        Dict with keys: type, language, content

    Raises:
        ValueError: If target is unknown or compilation fails
        FileNotFoundError: If Vegas JAR is not found
    """
    if target not in COMPILE_TARGETS:
        raise ValueError(
            f"Unknown compile target: {target}. Available: {list(COMPILE_TARGETS.keys())}"
        )

    target_info = COMPILE_TARGETS[target]

    if not VEGAS_JAR.exists():
        raise FileNotFoundError(f"Vegas JAR not found at {VEGAS_JAR}")

    # Ensure filename ends with .vg
    if not filename.endswith(".vg"):
        filename = filename + ".vg"

    with tempfile.TemporaryDirectory() as tmpdir:
        vg_path = Path(tmpdir) / filename
        vg_path.write_text(content, encoding="utf-8")

        logger.info("Running Vegas compiler on %s with target %s", vg_path, target)

        # Run Vegas to generate target output
        result = subprocess.run(
            ["java", "-jar", str(VEGAS_JAR), str(vg_path), target_info["flag"]],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = (
                result.stderr.strip() or result.stdout.strip() or "Unknown error"
            )
            logger.error("Vegas compilation failed: %s", error_msg)
            raise ValueError(f"Vegas compilation failed: {error_msg}")

        # Read the generated output file
        base_name = filename.removesuffix(".vg")
        output_path = Path(tmpdir) / f"{base_name}{target_info['extension']}"

        if not output_path.exists():
            raise ValueError(
                f"Vegas did not produce {target} output. Check the Vegas log."
            )

        output_content = output_path.read_text(encoding="utf-8")

        logger.info("Successfully compiled %s to %s", filename, target)
        return {
            "type": target_info["type"],
            "language": target_info["language"],
            "content": output_content,
        }
