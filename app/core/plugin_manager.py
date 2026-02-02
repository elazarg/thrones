"""Plugin discovery and health-checking for Docker Compose-managed services.

Discovers plugins by health-checking predefined URLs (from environment variables).
Plugins are managed by Docker Compose, not as subprocesses.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import tomllib

from app.config import PluginManagerConfig, PLUGIN_URLS

logger = logging.getLogger(__name__)


@dataclass
class PluginConfig:
    """Configuration for a single remote plugin."""

    name: str
    url: str = ""


@dataclass
class PluginProcess:
    """Runtime state for a plugin service (Docker container)."""

    config: PluginConfig
    url: str = ""
    healthy: bool = False
    info: dict[str, Any] = field(default_factory=dict)
    analyses: list[dict[str, Any]] = field(default_factory=list)


def load_plugins_toml(path: str | Path) -> tuple[dict[str, Any], list[PluginConfig]]:
    """Load and parse plugins.toml, returning (settings, plugin_configs).

    In Docker mode, we only need plugin names - URLs come from environment.
    """
    path = Path(path)
    if not path.exists():
        return {}, []

    with open(path, "rb") as f:
        data = tomllib.load(f)

    settings = data.get("settings", {})
    plugins = []
    for entry in data.get("plugins", []):
        name = entry["name"]
        # URL comes from environment variables only
        url = PLUGIN_URLS.get(name, "")
        plugins.append(PluginConfig(name=name, url=url))

    return settings, plugins


class PluginManager:
    """Discovers and health-checks Docker Compose-managed plugin services."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        startup_timeout: float = PluginManagerConfig.STARTUP_TIMEOUT_SECONDS,
    ):
        self._config_path = config_path
        self._startup_timeout = startup_timeout
        self._plugins: dict[str, PluginProcess] = {}
        self._project_root: Path = Path.cwd()
        self._loading: bool = False
        self._loading_plugins: set[str] = set()
        self._startup_results: dict[str, bool] = {}
        # Track registered plugins (for incremental registration)
        self._registered_plugins: set[str] = set()
        self._registration_lock = __import__("threading").Lock()

    def load_config(self, project_root: Path | None = None) -> None:
        """Load plugin configuration from plugins.toml and environment."""
        if project_root:
            self._project_root = project_root

        config_path = self._config_path or (self._project_root / "plugins.toml")
        settings, plugin_configs = load_plugins_toml(config_path)

        self._startup_timeout = settings.get(
            "startup_timeout_seconds", self._startup_timeout
        )

        for pc in plugin_configs:
            pp = PluginProcess(config=pc, url=pc.url)
            self._plugins[pc.name] = pp

    def start_all(self, background: bool = False) -> dict[str, bool]:
        """Discover all plugins by health-checking Docker containers.

        If background=True, returns immediately and discovers plugins in a thread.
        Check is_loading and loading_status for progress.
        """
        if not self._plugins:
            return {}

        self._loading = True
        self._loading_plugins = set(self._plugins.keys())
        self._startup_results = {}

        def _do_discover():
            # Check plugins in parallel for faster startup
            with ThreadPoolExecutor(max_workers=len(self._plugins)) as executor:
                futures = {
                    name: executor.submit(self._discover_plugin_tracked, name, pp)
                    for name, pp in self._plugins.items()
                }
                for name, fut in futures.items():
                    self._startup_results[name] = fut.result()

            self._loading = False

        if background:
            import threading

            thread = threading.Thread(target=_do_discover, daemon=True)
            thread.start()
            return {}  # Results not available yet
        else:
            _do_discover()
            return self._startup_results

    def _discover_plugin_tracked(self, name: str, pp: PluginProcess) -> bool:
        """Discover plugin and update loading state."""
        try:
            return self._discover_plugin(pp)
        finally:
            self._loading_plugins.discard(name)

    def _discover_plugin(self, pp: PluginProcess) -> bool:
        """Health-check a plugin and fetch its info if healthy."""
        if not pp.url:
            logger.warning("No URL configured for plugin %s", pp.config.name)
            return False

        logger.info("Discovering plugin %s at %s", pp.config.name, pp.url)

        # Wait for health
        health_result = self._wait_for_health(pp)
        if health_result is True:
            pp.healthy = True
            self._fetch_info(pp)
            logger.info(
                "Plugin %s healthy at %s (%d analyses)",
                pp.config.name,
                pp.url,
                len(pp.analyses),
            )
            return True

        if health_result == "degraded":
            pp.healthy = False
            logger.info(
                "Plugin %s started in degraded mode at %s", pp.config.name, pp.url
            )
            return True  # Still counts as "discovered"

        logger.warning("Plugin %s not reachable at %s", pp.config.name, pp.url)
        return False

    def _wait_for_health(
        self, pp: PluginProcess, timeout: float | None = None
    ) -> bool | str:
        """Poll /health with exponential backoff.

        Returns:
            True if healthy, False if failed to respond, or "degraded" if plugin
            responded with error status (running but not functional).
        """
        timeout = timeout or self._startup_timeout
        deadline = time.monotonic() + timeout
        interval = PluginManagerConfig.HEALTH_CHECK_INITIAL_INTERVAL

        while time.monotonic() < deadline:
            try:
                resp = httpx.get(
                    f"{pp.url}/health",
                    timeout=PluginManagerConfig.HEALTH_CHECK_TIMEOUT_SECONDS,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok" and data.get("api_version") == 1:
                        return True
                    # Plugin explicitly reports error status (e.g., platform not supported)
                    if data.get("status") == "error":
                        error_msg = data.get("error", "Unknown error")
                        logger.warning(
                            "Plugin %s started but degraded: %s",
                            pp.config.name,
                            error_msg,
                        )
                        pp.info = {"error": error_msg, "status": "error"}
                        return "degraded"
                    logger.warning(
                        "Plugin %s health response unexpected: %s",
                        pp.config.name,
                        data,
                    )
            except (httpx.ConnectError, httpx.TimeoutException):
                # Expected during startup - container not ready yet
                logger.debug(
                    "Plugin %s not ready yet (connection/timeout)", pp.config.name
                )
            except httpx.HTTPStatusError as e:
                logger.debug("Health check HTTP error for %s: %s", pp.config.name, e)

            time.sleep(interval)
            interval = min(
                interval * PluginManagerConfig.HEALTH_CHECK_BACKOFF_FACTOR,
                PluginManagerConfig.HEALTH_CHECK_MAX_INTERVAL,
            )

        return False

    def _fetch_info(self, pp: PluginProcess) -> None:
        """Fetch /info from a healthy plugin."""
        try:
            resp = httpx.get(
                f"{pp.url}/info",
                timeout=PluginManagerConfig.INFO_FETCH_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            pp.info = resp.json()
            pp.analyses = pp.info.get("analyses", [])
        except httpx.RequestError as e:
            logger.warning("Failed to fetch /info from %s: %s", pp.config.name, e)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP error fetching /info from %s: %s", pp.config.name, e)

    def get_plugin(self, name: str) -> PluginProcess | None:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def healthy_plugins(self) -> list[PluginProcess]:
        """Return all currently healthy plugins."""
        return [pp for pp in self._plugins.values() if pp.healthy]

    def stop_all(self) -> None:
        """No-op: Docker Compose manages container lifecycle."""
        logger.info("stop_all called - containers managed by Docker Compose")

    @property
    def plugins(self) -> dict[str, PluginProcess]:
        """Access all plugins."""
        return self._plugins

    @property
    def is_loading(self) -> bool:
        """True while plugins are being discovered."""
        return self._loading

    @property
    def loading_status(self) -> dict[str, Any]:
        """Return current loading status for display."""
        total = len(self._plugins)
        loading = list(self._loading_plugins)
        ready = len(self._startup_results)

        return {
            "loading": self._loading,
            "total_plugins": total,
            "plugins_ready": ready,
            "plugins_loading": loading,
            "progress": ready / total if total > 0 else 1.0,
        }

    def is_registered(self, name: str) -> bool:
        """Check if a plugin has been registered."""
        return name in self._registered_plugins

    def mark_registered(self, name: str) -> bool:
        """Mark a plugin as registered (thread-safe).

        Returns True if newly registered, False if already registered.
        """
        with self._registration_lock:
            if name in self._registered_plugins:
                return False
            self._registered_plugins.add(name)
            return True

    @property
    def registered_plugins(self) -> set[str]:
        """Return set of registered plugin names."""
        return self._registered_plugins.copy()
