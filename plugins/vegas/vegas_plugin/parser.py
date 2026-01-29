"""Parse .vg files using the Vegas JAR."""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to Vegas JAR - relative to this file's location
VEGAS_JAR = Path(__file__).parent.parent / "lib" / "vegas.jar"


def parse_vg(content: str, filename: str = "game.vg") -> dict[str, Any]:
    """Parse a .vg file and return a MAID game dict.

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
        ValueError: If parsing fails
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
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            logger.error("Vegas compilation failed: %s", error_msg)
            raise ValueError(f"Vegas compilation failed: {error_msg}")

        # Read the generated MAID JSON file
        base_name = filename.removesuffix(".vg")
        maid_path = Path(tmpdir) / f"{base_name}.maid.json"

        if not maid_path.exists():
            raise ValueError("Vegas did not produce MAID output. Check the Vegas log.")

        maid_content = maid_path.read_text(encoding="utf-8")
        game = json.loads(maid_content)

        logger.info("Successfully parsed %s to MAID", filename)
        return game
