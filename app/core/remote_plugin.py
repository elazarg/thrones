"""HTTP adapter that makes a remote plugin service look like a local AnalysisPlugin."""

from __future__ import annotations

import logging
from threading import Event

from app.config import RemotePluginConfig
from app.core.http_client import RemoteServiceClient, RemoteServiceError
from app.core.registry import AnalysisResult
from shared import export_to_efg

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
        self.applicable_to: tuple[str, ...] = tuple(
            analysis_info.get("applicable_to", ())
        )
        self.continuous: bool = analysis_info.get("continuous", True)
        self._config_schema: dict = analysis_info.get("config_schema", {})
        self._client = RemoteServiceClient(base_url, service_name=self.name)

    def can_run(self, game) -> bool:
        """Check if this plugin can analyze the given game (native or via conversion)."""
        native_format = getattr(game, "format_name", None)
        if native_format is None:
            return False

        if native_format in self.applicable_to:
            return True

        # Check if game can be converted to a supported format
        from app.dependencies import get_conversion_registry

        conversion_registry = get_conversion_registry()
        for target_format in self.applicable_to:
            check = conversion_registry.check(game, target_format, quick=True)
            if check.possible:
                return True
        return False

    def _prepare_game_data(self, game) -> tuple[dict | None, AnalysisResult | None]:
        """Convert game to required format. Returns (game_data, error_result)."""
        from app.dependencies import get_conversion_registry

        native_format = getattr(game, "format_name", None)
        conversion_registry = get_conversion_registry()

        # Find a format we can provide
        for target_format in self.applicable_to:
            if native_format == target_format:
                game_data = game.model_dump()
            else:
                check = conversion_registry.check(game, target_format, quick=True)
                if not check.possible:
                    continue
                try:
                    converted = conversion_registry.convert(game, target_format)
                    game_data = converted.model_dump()
                except ValueError as e:
                    continue  # Try next format

            # Add EFG content for extensive-form games
            if target_format == "extensive":
                try:
                    game_data["efg_content"] = export_to_efg(game_data)
                except ValueError as e:
                    return None, AnalysisResult(
                        summary=f"Error: EFG export failed: {e}",
                        details={
                            "error": {"code": "EFG_EXPORT_FAILED", "message": str(e)}
                        },
                    )

            return game_data, None

        # No format worked
        return None, AnalysisResult(
            summary=f"Error: Cannot convert to required format ({', '.join(self.applicable_to)})",
            details={
                "error": {
                    "code": "NO_CONVERSION",
                    "message": f"Game cannot be converted to {self.applicable_to}",
                }
            },
        )

    def run(self, game, config: dict | None = None) -> AnalysisResult:
        """Submit analysis to remote plugin and poll for result."""
        config = config or {}
        cancel_event: Event | None = config.get("_cancel_event")

        # Strip internal keys that don't serialize
        clean_config = {k: v for k, v in config.items() if not k.startswith("_")}

        # Convert game to required format
        game_data, error = self._prepare_game_data(game)
        if error:
            return error

        # Submit analysis
        try:
            task = self._client.post(
                "/analyze",
                json={
                    "analysis": self.name,
                    "game": game_data,
                    "config": clean_config,
                },
                timeout=RemotePluginConfig.SUBMIT_TIMEOUT_SECONDS,
            )
        except RemoteServiceError as e:
            return AnalysisResult(
                summary=f"Error: {e.error.message}",
                details={"error": e.error.to_dict()},
            )

        # Poll until done
        task_id = task["task_id"]
        try:
            task = self._client.poll_until_complete(task_id, cancel_event=cancel_event)
        except RemoteServiceError as e:
            return AnalysisResult(
                summary=f"Error: lost connection during analysis ({e.error.message})",
                details={"error": e.error.to_dict()},
            )

        if task.get("status") == "failed":
            error = task.get("error", {})
            return AnalysisResult(
                summary=f"Error: {error.get('message', 'unknown')}",
                details={"error": error},
            )

        if task.get("status") == "cancelled" or task.get("cancelled"):
            return AnalysisResult(
                summary="Cancelled",
                details={"cancelled": True},
            )

        # Success - status is "completed" (normalized from plugin's "done")
        result_data = task.get("result", {})
        return AnalysisResult(
            summary=result_data.get("summary", "Analysis complete"),
            details=result_data.get("details", {}),
        )

    def summarize(self, result: AnalysisResult) -> str:
        """Return the summary from the result."""
        return result.summary
