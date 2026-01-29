"""Subprocess supervisor for remote plugin services.

Manages plugin processes: launches them on dynamic ports, health-checks,
restarts on failure, and shuts down cleanly.
"""
from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import tomllib

from app.config import PluginManagerConfig

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"


@dataclass
class PluginConfig:
    """Configuration for a single remote plugin."""

    name: str
    command: list[str]
    cwd: str = "."
    auto_start: bool = True
    restart: str = "on-failure"  # never | on-failure | always


@dataclass
class PluginProcess:
    """Runtime state for a managed plugin process."""

    config: PluginConfig
    port: int = 0
    process: subprocess.Popen | None = None
    url: str = ""
    healthy: bool = False
    restart_count: int = 0
    info: dict[str, Any] = field(default_factory=dict)
    analyses: list[dict[str, Any]] = field(default_factory=list)


def _find_free_port() -> int:
    """Ask the OS for a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def load_plugins_toml(path: str | Path) -> tuple[dict[str, Any], list[PluginConfig]]:
    """Load and parse plugins.toml, returning (settings, plugin_configs)."""
    path = Path(path)
    if not path.exists():
        return {}, []

    with open(path, "rb") as f:
        data = tomllib.load(f)

    settings = data.get("settings", {})
    plugins = []
    for entry in data.get("plugins", []):
        plugins.append(
            PluginConfig(
                name=entry["name"],
                command=entry["command"],
                cwd=entry.get("cwd", "."),
                auto_start=entry.get("auto_start", True),
                restart=entry.get("restart", "on-failure"),
            )
        )
    return settings, plugins


class PluginManager:
    """Manages remote plugin subprocess lifecycles."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        startup_timeout: float = PluginManagerConfig.STARTUP_TIMEOUT_SECONDS,
        max_restarts: int = PluginManagerConfig.MAX_RESTARTS,
    ):
        self._config_path = config_path
        self._startup_timeout = startup_timeout
        self._max_restarts = max_restarts
        self._plugins: dict[str, PluginProcess] = {}
        self._project_root: Path = Path.cwd()

    def load_config(self, project_root: Path | None = None) -> None:
        """Load plugin configuration from plugins.toml."""
        if project_root:
            self._project_root = project_root

        config_path = self._config_path or (self._project_root / "plugins.toml")
        settings, plugin_configs = load_plugins_toml(config_path)

        self._startup_timeout = settings.get(
            "startup_timeout_seconds", self._startup_timeout
        )
        self._max_restarts = settings.get("max_restarts", self._max_restarts)

        for pc in plugin_configs:
            self._plugins[pc.name] = PluginProcess(config=pc)

    def start_all(self) -> dict[str, bool]:
        """Start all auto_start plugins in parallel. Returns {name: success}."""
        to_start = {name: pp for name, pp in self._plugins.items() if pp.config.auto_start}

        if not to_start:
            return {name: False for name in self._plugins}

        # Start plugins in parallel to reduce total startup time
        with ThreadPoolExecutor(max_workers=len(to_start)) as executor:
            futures = {name: executor.submit(self._start_plugin, pp) for name, pp in to_start.items()}
            results = {name: fut.result() for name, fut in futures.items()}

        # Add non-auto-start plugins as False
        for name in self._plugins:
            if name not in results:
                results[name] = False

        return results

    def _start_plugin(
        self, pp: PluginProcess, max_port_retries: int = PluginManagerConfig.MAX_PORT_RETRIES
    ) -> bool:
        """Start a single plugin subprocess and wait for health.

        Retries with fresh port allocation to mitigate TOCTOU race conditions
        where another process grabs the port between allocation and binding.
        """
        cwd = self._project_root / pp.config.cwd

        for attempt in range(max_port_retries):
            port = _find_free_port()
            pp.port = port
            pp.url = f"http://127.0.0.1:{port}"

            # Resolve the executable path relative to project root so it works
            # regardless of the parent process's working directory.
            raw_cmd = list(pp.config.command) + [f"--port={port}"]
            exe_path = self._project_root / raw_cmd[0]
            cmd = [str(exe_path)] + raw_cmd[1:]

            logger.info(
                "Starting plugin %s on port %d: %s (cwd=%s)",
                pp.config.name, port, " ".join(cmd), cwd,
            )

            try:
                creation_flags = 0
                if _IS_WINDOWS:
                    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

                # Use DEVNULL for stdout/stderr to prevent pipe buffer deadlocks.
                # If a plugin writes too much output without the parent reading,
                # the pipe buffers fill up and the plugin blocks on writes,
                # making it unresponsive to health checks.
                pp.process = subprocess.Popen(
                    cmd,
                    cwd=str(cwd),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation_flags,
                )
            except (FileNotFoundError, OSError) as e:
                logger.error("Failed to launch plugin %s: %s", pp.config.name, e)
                return False

            # Wait for health
            if self._wait_for_health(pp):
                pp.healthy = True
                self._fetch_info(pp)
                logger.info(
                    "Plugin %s healthy on port %d (%d analyses)",
                    pp.config.name, port, len(pp.analyses),
                )
                return True

            # Health check failed - could be port conflict (TOCTOU race)
            self._kill(pp)
            if attempt < max_port_retries - 1:
                logger.warning(
                    "Plugin %s failed on port %d, retrying with new port (attempt %d/%d)",
                    pp.config.name, port, attempt + 2, max_port_retries,
                )

        logger.error("Plugin %s failed after %d attempts", pp.config.name, max_port_retries)
        return False

    def _wait_for_health(self, pp: PluginProcess, timeout: float | None = None) -> bool:
        """Poll /health with exponential backoff."""
        timeout = timeout or self._startup_timeout
        deadline = time.monotonic() + timeout
        interval = PluginManagerConfig.HEALTH_CHECK_INITIAL_INTERVAL

        while time.monotonic() < deadline:
            # Check process is still alive
            if pp.process and pp.process.poll() is not None:
                logger.warning(
                    "Plugin %s exited with code %d during startup",
                    pp.config.name, pp.process.returncode,
                )
                return False

            try:
                resp = httpx.get(
                    f"{pp.url}/health",
                    timeout=PluginManagerConfig.HEALTH_CHECK_TIMEOUT_SECONDS,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok" and data.get("api_version") == 1:
                        return True
                    logger.warning(
                        "Plugin %s health response unexpected: %s",
                        pp.config.name, data,
                    )
            except (httpx.ConnectError, httpx.TimeoutException):
                # Expected during startup - plugin not ready yet
                logger.debug("Plugin %s not ready yet (connection/timeout)", pp.config.name)
            except httpx.HTTPStatusError as e:
                logger.debug(
                    "Health check HTTP error for %s: %s", pp.config.name, e
                )

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

    def _kill(self, pp: PluginProcess) -> None:
        """Terminate a plugin process."""
        if pp.process is None:
            return
        try:
            if _IS_WINDOWS:
                # On Windows, send CTRL_BREAK_EVENT to the process group
                os.kill(pp.process.pid, signal.CTRL_BREAK_EVENT)
            else:
                pp.process.terminate()
            pp.process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            # Graceful termination failed - force kill
            try:
                pp.process.kill()
                pp.process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired) as e:
                # Process may already be dead or unresponsive - continue cleanup
                logger.debug("Force kill cleanup for %s: %s", pp.config.name, e)
        pp.process = None
        pp.healthy = False

    def restart_plugin(self, name: str) -> bool:
        """Restart a plugin by name."""
        pp = self._plugins.get(name)
        if pp is None:
            return False
        self._kill(pp)
        pp.restart_count += 1
        return self._start_plugin(pp)

    def check_and_restart(self) -> dict[str, str]:
        """Check all plugins and restart crashed ones per policy.

        Returns {name: action} where action is 'ok', 'restarted', 'dead', 'skipped'.
        """
        results = {}
        for name, pp in self._plugins.items():
            if not pp.config.auto_start:
                results[name] = "skipped"
                continue

            if pp.process is None or pp.process.poll() is not None:
                # Process has exited
                if pp.config.restart == "never":
                    results[name] = "dead"
                    pp.healthy = False
                elif pp.config.restart == "on-failure" and pp.restart_count < self._max_restarts:
                    # Increment count BEFORE attempting restart (counts attempts, not successes)
                    pp.restart_count += 1
                    logger.info(
                        "Restarting crashed plugin %s (attempt %d/%d)",
                        name, pp.restart_count, self._max_restarts,
                    )
                    if self._start_plugin(pp):
                        results[name] = "restarted"
                    else:
                        results[name] = "dead"
                        pp.healthy = False
                elif pp.config.restart == "always":
                    pp.restart_count += 1
                    if self._start_plugin(pp):
                        results[name] = "restarted"
                    else:
                        results[name] = "dead"
                        pp.healthy = False
                else:
                    results[name] = "dead"
                    pp.healthy = False
            else:
                results[name] = "ok"

        return results

    def get_plugin(self, name: str) -> PluginProcess | None:
        """Get a managed plugin by name."""
        return self._plugins.get(name)

    def healthy_plugins(self) -> list[PluginProcess]:
        """Return all currently healthy plugins."""
        return [pp for pp in self._plugins.values() if pp.healthy]

    def stop_all(self) -> None:
        """Stop all managed plugin processes."""
        for name, pp in self._plugins.items():
            if pp.process is not None:
                logger.info("Stopping plugin %s", name)
                self._kill(pp)

    @property
    def plugins(self) -> dict[str, PluginProcess]:
        """Access all managed plugins."""
        return self._plugins
