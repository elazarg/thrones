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

from vegas_plugin.parser import (
    parse_vg,
    compile_to_maid,
    compile_to_target,
    COMPILE_TARGETS,
)

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


class CompileRequest(BaseModel):
    source_code: str
    filename: str = "game.vg"


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Vegas Plugin", version=PLUGIN_VERSION)


class _HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) < 5:
            return True
        path, status = args[2], args[4]
        return not (isinstance(path, str) and path.endswith("/health") and status == 200)


@app.on_event("startup")
def _suppress_health_logs() -> None:
    f = _HealthCheckFilter()
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addFilter(f)
    for handler in access_logger.handlers:
        handler.addFilter(f)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
    }


@app.get("/info")
def info() -> dict:
    # Build compile_targets list from COMPILE_TARGETS dict
    compile_targets = [
        {
            "id": t["id"],
            "type": t["type"],
            "language": t["language"],
            "label": t["label"],
        }
        for t in COMPILE_TARGETS.values()
    ]

    return {
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
        "analyses": [],  # Vegas provides parsing/conversion, not analyses
        "formats": [".vg"],
        "conversions": [
            {"source": "vegas", "target": "maid"},
        ],
        "compile_targets": compile_targets,
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


@app.post("/compile/{target}")
def compile_endpoint(target: str, req: CompileRequest) -> dict:
    """Compile Vegas source to a specific target (solidity, vyper, smt, scribble).

    Returns dict with: type, language, content
    """
    try:
        result = compile_to_target(req.source_code, target, req.filename)
        return result
    except ValueError as e:
        logger.exception("Compile error")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "COMPILE_ERROR",
                    "message": str(e),
                }
            },
        )
    except FileNotFoundError as e:
        logger.exception("Vegas JAR not found")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL",
                    "message": str(e),
                }
            },
        )
    except Exception as e:
        logger.exception("Compile failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL",
                    "message": f"Compile failed: {e}",
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
