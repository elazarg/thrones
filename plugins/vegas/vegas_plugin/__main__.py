"""Vegas plugin service entrypoint.

Run with: python -m vegas_plugin --port=PORT
Implements the plugin HTTP contract (API v1).
"""
from __future__ import annotations

import argparse
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from vegas_plugin.parser import parse_vg, compile_to_maid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vegas_plugin")

PLUGIN_VERSION = "0.1.0"
API_VERSION = 1

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ParseRequest(BaseModel):
    content: str
    filename: str = "game.vg"


class ConvertRequest(BaseModel):
    game: dict[str, Any]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Vegas Plugin", version=PLUGIN_VERSION)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
    }


@app.get("/info")
def info() -> dict:
    return {
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
        "analyses": [],  # Vegas provides parsing/conversion, not analyses
        "formats": [".vg"],
        "conversions": [
            {"source": "vegas", "target": "maid"},
        ],
    }


@app.post("/parse/vg")
def parse_vg_endpoint(req: ParseRequest) -> dict:
    """Parse a .vg file and return VegasGame dict."""
    try:
        game = parse_vg(req.content, req.filename)
        return {"game": game}
    except ValueError as e:
        logger.exception("Parse error")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e),
                }
            },
        )
    except Exception as e:
        logger.exception("Parse failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL",
                    "message": f"Parse failed: {e}",
                }
            },
        )


@app.post("/convert/vegas-to-maid")
def convert_vegas_to_maid(req: ConvertRequest) -> dict:
    """Convert a VegasGame to MAIDGame by compiling the source code."""
    try:
        vegas_game = req.game
        source_code = vegas_game.get("source_code")
        if not source_code:
            raise ValueError("VegasGame has no source_code")

        title = vegas_game.get("title", "game")
        maid_game = compile_to_maid(source_code, f"{title}.vg")

        return {"game": maid_game}
    except ValueError as e:
        logger.exception("Conversion error")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CONVERSION_ERROR",
                    "message": str(e),
                }
            },
        )
    except Exception as e:
        logger.exception("Conversion failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL",
                    "message": f"Conversion failed: {e}",
                }
            },
        )


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Vegas plugin service")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    logger.info("Starting Vegas plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
