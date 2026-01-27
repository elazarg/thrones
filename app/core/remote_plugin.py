"""HTTP adapter that makes a remote plugin service look like a local AnalysisPlugin."""
from __future__ import annotations

import logging
import time
from threading import Event

import httpx

from app.core.registry import AnalysisResult

logger = logging.getLogger(__name__)


class RemotePlugin:
    """Adapter: makes an HTTP plugin service look like a local AnalysisPlugin.

    Each remote analysis endpoint is wrapped as a separate RemotePlugin instance,
    so one plugin service (e.g. gambit) can expose multiple analyses (Nash, IESDS, etc.).
    """

    def __init__(self, base_url: str, analysis_info: dict):
        self.base_url = base_url
        self.name: str = analysis_info["name"]
        self.description: str = analysis_info.get("description", "")
        self.applicable_to: tuple[str, ...] = tuple(analysis_info.get("applicable_to", ()))
        self.continuous: bool = analysis_info.get("continuous", True)
        self._config_schema: dict = analysis_info.get("config_schema", {})

    def can_run(self, game) -> bool:
        """Check if this plugin can analyze the given game."""
        return getattr(game, "format_name", None) in self.applicable_to

    def run(self, game, config: dict | None = None) -> AnalysisResult:
        """Submit analysis to remote plugin and poll for result."""
        config = config or {}
        cancel_event: Event | None = config.get("_cancel_event")

        # Strip internal keys that don't serialize
        clean_config = {k: v for k, v in config.items() if not k.startswith("_")}

        # Submit analysis
        try:
            resp = httpx.post(
                f"{self.base_url}/analyze",
                json={
                    "analysis": self.name,
                    "game": game.model_dump(),
                    "config": clean_config,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            task = resp.json()
        except httpx.HTTPStatusError as e:
            error_body = {}
            try:
                error_body = e.response.json()
            except Exception:
                pass
            error_msg = error_body.get("error", {}).get("message", str(e))
            return AnalysisResult(
                summary=f"Error: {error_msg}",
                details={"error": error_body.get("error", {"message": str(e)})},
            )
        except Exception as e:
            return AnalysisResult(
                summary=f"Error: plugin unreachable ({e})",
                details={"error": {"code": "UNREACHABLE", "message": str(e)}},
            )

        # Poll until done
        task_id = task["task_id"]
        poll_url = f"{self.base_url}/tasks/{task_id}"
        interval = 0.1

        while task["status"] in ("queued", "running"):
            # Check cancellation
            if cancel_event is not None and cancel_event.is_set():
                self._cancel_remote(task_id)
                return AnalysisResult(
                    summary="Cancelled",
                    details={"cancelled": True},
                )

            time.sleep(interval)
            interval = min(interval * 1.3, 1.0)

            try:
                resp = httpx.get(poll_url, timeout=5.0)
                resp.raise_for_status()
                task = resp.json()
            except Exception as e:
                logger.warning("Poll failed for %s task %s: %s", self.name, task_id, e)
                return AnalysisResult(
                    summary=f"Error: lost connection during analysis ({e})",
                    details={"error": {"code": "POLL_FAILED", "message": str(e)}},
                )

        if task["status"] == "failed":
            error = task.get("error", {})
            return AnalysisResult(
                summary=f"Error: {error.get('message', 'unknown')}",
                details={"error": error},
            )

        if task["status"] == "cancelled":
            return AnalysisResult(
                summary="Cancelled",
                details={"cancelled": True},
            )

        # Success
        result_data = task.get("result", {})
        return AnalysisResult(
            summary=result_data.get("summary", "Analysis complete"),
            details=result_data.get("details", {}),
        )

    def _cancel_remote(self, task_id: str) -> None:
        """Best-effort cancel on the remote plugin."""
        try:
            httpx.post(
                f"{self.base_url}/cancel/{task_id}",
                timeout=2.0,
            )
        except Exception:
            pass

    def summarize(self, result: AnalysisResult) -> str:
        """Return the summary from the result."""
        return result.summary
