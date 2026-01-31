"""Centralized configuration constants for the application.

Consolidates magic numbers and configuration values that were previously
scattered throughout the codebase.
"""

from __future__ import annotations

import os

# Plugin URLs from environment variables (for Docker Compose)
PLUGIN_URLS: dict[str, str] = {
    "gambit": os.environ.get("GAMBIT_URL", "http://gambit:5001"),
    "pycid": os.environ.get("PYCID_URL", "http://pycid:5002"),
    "egttools": os.environ.get("EGTTOOLS_URL", "http://egttools:5003"),
    "vegas": os.environ.get("VEGAS_URL", "http://vegas:5004"),
    "openspiel": os.environ.get("OPENSPIEL_URL", "http://openspiel:5005"),
}


class PluginManagerConfig:
    """Configuration constants for plugin discovery and health-checking."""

    # Startup and health check
    # PyCID plugin takes ~30s to import libraries on first load
    STARTUP_TIMEOUT_SECONDS = 60.0
    HEALTH_CHECK_TIMEOUT_SECONDS = 2.0
    INFO_FETCH_TIMEOUT_SECONDS = 5.0

    # Polling intervals
    HEALTH_CHECK_INITIAL_INTERVAL = 0.1
    HEALTH_CHECK_MAX_INTERVAL = 1.0
    HEALTH_CHECK_BACKOFF_FACTOR = 1.5


class RemotePluginConfig:
    """Configuration constants for remote plugin communication."""

    # HTTP timeouts
    SUBMIT_TIMEOUT_SECONDS = 10.0
    POLL_TIMEOUT_SECONDS = 5.0
    CANCEL_TIMEOUT_SECONDS = 2.0

    # Polling behavior
    POLL_INITIAL_INTERVAL = 0.1
    POLL_MAX_INTERVAL = 1.0
    POLL_BACKOFF_FACTOR = 1.3
    POLL_MAX_DURATION_SECONDS = 300.0  # 5 minutes max for any single task


class ConversionConfig:
    """Configuration constants for game format conversions."""

    # Strategy enumeration limits (for EFG to NFG conversion)
    STRATEGY_COUNT_WARNING_THRESHOLD = 100
    STRATEGY_COUNT_BLOCKING_THRESHOLD = 10000


class TaskConfig:
    """Configuration constants for async task management."""

    TASK_ID_LENGTH = 8
    DEFAULT_MAX_WORKERS = 4
    TASK_CLEANUP_MAX_AGE_SECONDS = 3600


class RemoteFormatConfig:
    """Configuration constants for remote format parsing."""

    PARSE_TIMEOUT_SECONDS = 30.0
    CONVERT_TIMEOUT_SECONDS = 30.0
