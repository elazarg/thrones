"""Centralized configuration constants for the application.

Consolidates magic numbers and configuration values that were previously
scattered throughout the codebase.
"""

from __future__ import annotations

import os

# Environment mode
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# CORS configuration
# In production, restrict to specific origins; in development, allow localhost
_cors_origins_env = os.environ.get("CORS_ORIGINS", "")
if _cors_origins_env:
    CORS_ORIGINS: list[str] = [origin.strip() for origin in _cors_origins_env.split(",")]
elif IS_PRODUCTION:
    # Production requires explicit CORS_ORIGINS to be set
    CORS_ORIGINS = []
else:
    # Development defaults
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

# File upload limits
MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 5 * 1024 * 1024))  # 5MB default

# Plugin URLs from environment variables.
# Defaults use Docker service names (works inside Docker Compose network).
# Docker Compose also sets these explicitly via the environment: block.
# For running the app outside Docker, set env vars to http://localhost:<port>.
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

    # HTTP timeouts (per-request)
    # These must be long enough to allow the plugin to respond while CPU-bound
    SUBMIT_TIMEOUT_SECONDS = 30.0
    POLL_TIMEOUT_SECONDS = 30.0
    CANCEL_TIMEOUT_SECONDS = 5.0

    # Polling behavior
    POLL_INITIAL_INTERVAL = 0.1
    POLL_MAX_INTERVAL = 2.0
    POLL_BACKOFF_FACTOR = 1.5
    POLL_MAX_DURATION_SECONDS = 60.0  # Default timeout; can be overridden per-request


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
