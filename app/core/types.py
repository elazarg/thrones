"""Shared type definitions for the application.

This module provides TypedDict and Literal types for commonly used
dictionary structures, improving type safety and IDE support.
"""

from __future__ import annotations

from typing import Literal, TypedDict

# =============================================================================
# Plugin Types
# =============================================================================


class AnalysisInfo(TypedDict):
    """Information about an analysis provided by a plugin."""

    name: str
    description: str
    applicable_to: list[str]
    continuous: bool
    config_schema: dict  # JSON Schema for config options


class ConversionInfo(TypedDict):
    """Information about a format conversion provided by a plugin."""

    source: str
    target: str


class PluginInfo(TypedDict, total=False):
    """Full plugin info as returned by /info endpoint."""

    name: str
    version: str
    analyses: list[AnalysisInfo]
    formats: list[str]
    conversions: list[ConversionInfo]
    compile_targets: list[str]
    error: str  # Present if plugin is degraded


class LoadingStatus(TypedDict):
    """Plugin loading progress status."""

    loading: bool
    total_plugins: int
    plugins_ready: int
    plugins_loading: list[str]
    progress: float  # 0.0 to 1.0


# =============================================================================
# Status Literals
# =============================================================================

PluginStatus = Literal["ready", "loading", "degraded", "unavailable"]
TaskStatusLiteral = Literal["pending", "running", "completed", "failed", "cancelled"]
GameFormat = Literal["extensive", "normal", "maid"]
HealthStatus = Literal["ok", "error", "loading"]


# =============================================================================
# Error Types
# =============================================================================


class ErrorDetail(TypedDict, total=False):
    """Standard error detail structure."""

    code: str
    message: str
    details: dict
