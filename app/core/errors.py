"""Standardized error handling utilities for API routes.

Provides consistent error response formatting across all endpoints.
"""
from __future__ import annotations

from fastapi import HTTPException


def not_found(resource_type: str, resource_id: str) -> HTTPException:
    """Create a 404 Not Found exception with consistent formatting.

    Args:
        resource_type: Type of resource (e.g., "Game", "Task", "Plugin")
        resource_id: The identifier that was not found

    Returns:
        HTTPException with status 404
    """
    return HTTPException(
        status_code=404,
        detail=f"{resource_type} not found: {resource_id}",
    )


def bad_request(message: str) -> HTTPException:
    """Create a 400 Bad Request exception.

    Args:
        message: Description of what was wrong with the request

    Returns:
        HTTPException with status 400
    """
    return HTTPException(status_code=400, detail=message)


def invalid_format(format_name: str, error_type: str | None = None) -> HTTPException:
    """Create a 400 Bad Request exception for format errors.

    Args:
        format_name: The format that was invalid
        error_type: Optional error type name for debugging

    Returns:
        HTTPException with status 400
    """
    detail = f"Invalid game format: {format_name}"
    if error_type:
        detail = f"Invalid game format ({error_type}): {format_name}"
    return HTTPException(status_code=400, detail=detail)


def conversion_failed(source_format: str, target_format: str) -> HTTPException:
    """Create a 400 Bad Request exception for conversion failures.

    Args:
        source_format: The source format
        target_format: The target format that couldn't be reached

    Returns:
        HTTPException with status 400
    """
    return HTTPException(
        status_code=400,
        detail=f"Cannot convert from {source_format} to {target_format}",
    )


def plugin_unavailable(plugin_name: str, available: list[str]) -> HTTPException:
    """Create a 400 Bad Request exception for unknown plugins.

    Args:
        plugin_name: The plugin that wasn't found
        available: List of available plugin names

    Returns:
        HTTPException with status 400
    """
    return HTTPException(
        status_code=400,
        detail=f"Unknown plugin: {plugin_name}. Available: {available}",
    )


def incompatible_plugin(plugin_name: str, game_format: str) -> HTTPException:
    """Create a 400 Bad Request exception when plugin can't run on game.

    Args:
        plugin_name: The plugin name
        game_format: The game's format

    Returns:
        HTTPException with status 400
    """
    return HTTPException(
        status_code=400,
        detail=f"Plugin '{plugin_name}' cannot run on this game (format: {game_format})",
    )


def parse_failed() -> HTTPException:
    """Create a 500 Internal Server Error for parse failures.

    Returns:
        HTTPException with status 500
    """
    return HTTPException(status_code=500, detail="Failed to parse game file")


def safe_error_message(error: Exception) -> str:
    """Extract a safe error message from an exception.

    Avoids leaking internal details while preserving useful information.

    Args:
        error: The exception to extract message from

    Returns:
        A safe string representation of the error
    """
    # For ValueError, the message is usually safe to show
    if isinstance(error, ValueError):
        return str(error)
    # For other exceptions, just show the type
    return type(error).__name__
