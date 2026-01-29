"""Unified HTTP client for communicating with remote plugin services.

Centralizes HTTP communication patterns used by:
- Remote plugin analysis (remote_plugin.py)
- Remote format parsing (formats/remote.py)
- Remote conversions (conversions/remote.py)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Event
from typing import Any

import httpx

from app.config import RemotePluginConfig

logger = logging.getLogger(__name__)


@dataclass
class HTTPError:
    """Structured error from an HTTP request."""

    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class RemoteServiceError(Exception):
    """Exception raised when a remote service request fails."""

    def __init__(self, error: HTTPError):
        self.error = error
        super().__init__(error.message)


class RemoteServiceClient:
    """HTTP client for communicating with remote plugin services.

    Provides unified error handling, polling with exponential backoff,
    and consistent response parsing.

    Status Normalization:
        Plugins use different status names than the backend:
        - Plugin: queued, running, done, failed, cancelled
        - Backend: pending, running, completed, failed, cancelled

        This client normalizes plugin statuses to backend conventions
        when polling for task completion.
    """

    # Status values that plugins use (will be normalized)
    PLUGIN_PENDING_STATUSES = ("queued", "running")
    PLUGIN_DONE_STATUS = "done"
    PLUGIN_FAILED_STATUS = "failed"
    PLUGIN_CANCELLED_STATUS = "cancelled"

    # Mapping from plugin status names to backend status names
    STATUS_NORMALIZATION = {
        "queued": "pending",
        "done": "completed",
        # These are the same in both systems
        "running": "running",
        "failed": "failed",
        "cancelled": "cancelled",
    }

    def __init__(self, base_url: str, service_name: str = "remote"):
        """Initialize the client.

        Args:
            base_url: Base URL of the remote service (e.g., "http://127.0.0.1:5001")
            service_name: Human-readable name for error messages
        """
        self.base_url = base_url
        self.service_name = service_name

    def post(
        self,
        endpoint: str,
        json: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        """POST JSON to an endpoint and return the response.

        Args:
            endpoint: URL path (will be appended to base_url)
            json: Request body
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            RemoteServiceError: On HTTP errors or connection failures
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("POST %s", url)

        try:
            resp = httpx.post(url, json=json, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError as e:
            raise RemoteServiceError(
                HTTPError(
                    code="UNREACHABLE",
                    message=f"Service unreachable: {self.service_name}. {e}",
                )
            )
        except httpx.HTTPStatusError as e:
            error = self._extract_error(e.response)
            raise RemoteServiceError(error)
        except httpx.RequestError as e:
            raise RemoteServiceError(
                HTTPError(
                    code="REQUEST_ERROR",
                    message=f"Request failed: {e}",
                )
            )

    def get(
        self,
        endpoint: str,
        timeout: float,
    ) -> dict[str, Any]:
        """GET from an endpoint and return the response.

        Args:
            endpoint: URL path (will be appended to base_url)
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            RemoteServiceError: On HTTP errors or connection failures
        """
        url = f"{self.base_url}{endpoint}"

        try:
            resp = httpx.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError as e:
            raise RemoteServiceError(
                HTTPError(
                    code="UNREACHABLE",
                    message=f"Service unreachable: {self.service_name}. {e}",
                )
            )
        except httpx.HTTPStatusError as e:
            error = self._extract_error(e.response)
            raise RemoteServiceError(error)
        except httpx.RequestError as e:
            raise RemoteServiceError(
                HTTPError(
                    code="REQUEST_ERROR",
                    message=f"Request failed: {e}",
                )
            )

    def poll_until_complete(
        self,
        task_id: str,
        cancel_event: Event | None = None,
        initial_interval: float = RemotePluginConfig.POLL_INITIAL_INTERVAL,
        max_interval: float = RemotePluginConfig.POLL_MAX_INTERVAL,
        backoff_factor: float = RemotePluginConfig.POLL_BACKOFF_FACTOR,
        poll_timeout: float = RemotePluginConfig.POLL_TIMEOUT_SECONDS,
        max_duration: float = RemotePluginConfig.POLL_MAX_DURATION_SECONDS,
    ) -> dict[str, Any]:
        """Poll a task until it completes.

        Args:
            task_id: ID of the task to poll
            cancel_event: Optional threading.Event to signal cancellation
            initial_interval: Initial polling interval in seconds
            max_interval: Maximum polling interval in seconds
            backoff_factor: Multiplier for exponential backoff
            poll_timeout: Timeout for each poll request
            max_duration: Maximum total time to poll before giving up

        Returns:
            Final task state dict with normalized status

        Raises:
            RemoteServiceError: On polling failure or timeout
        """
        poll_url = f"/tasks/{task_id}"
        interval = initial_interval
        deadline = time.monotonic() + max_duration

        # Get initial task state
        task = self.get(poll_url, timeout=poll_timeout)

        while task.get("status") in self.PLUGIN_PENDING_STATUSES:
            # Check for cancellation
            if cancel_event is not None and cancel_event.is_set():
                self._cancel_task(task_id)
                return {"status": "cancelled", "cancelled": True}

            # Check for overall timeout
            if time.monotonic() >= deadline:
                logger.warning(
                    "Polling timeout for %s task %s after %.1fs",
                    self.service_name,
                    task_id,
                    max_duration,
                )
                raise RemoteServiceError(
                    HTTPError(
                        code="POLL_TIMEOUT",
                        message=f"Task {task_id} did not complete within {max_duration}s",
                    )
                )

            time.sleep(interval)
            interval = min(interval * backoff_factor, max_interval)

            try:
                task = self.get(poll_url, timeout=poll_timeout)
            except RemoteServiceError as e:
                logger.warning(
                    "Poll failed for %s task %s: %s",
                    self.service_name,
                    task_id,
                    e.error.message,
                )
                raise

        return self._normalize_task_status(task)

    def _normalize_task_status(self, task: dict[str, Any]) -> dict[str, Any]:
        """Normalize plugin status names to backend conventions.

        Plugins use 'queued' and 'done', while the backend uses 'pending' and 'completed'.
        This ensures consistent status handling across the system.
        """
        if "status" in task:
            original_status = task["status"]
            normalized = self.STATUS_NORMALIZATION.get(original_status, original_status)
            if normalized != original_status:
                task = task.copy()
                task["status"] = normalized
                logger.debug(
                    "Normalized task status: %s -> %s",
                    original_status,
                    normalized,
                )
        return task

    def _cancel_task(self, task_id: str) -> None:
        """Best-effort cancel on the remote service."""
        try:
            httpx.post(
                f"{self.base_url}/cancel/{task_id}",
                timeout=RemotePluginConfig.CANCEL_TIMEOUT_SECONDS,
            )
        except httpx.RequestError:
            # Best-effort - ignore network errors
            pass

    @staticmethod
    def _extract_error(response: httpx.Response) -> HTTPError:
        """Extract error information from an HTTP response.

        Handles various response formats:
        - {"error": {"code": ..., "message": ...}}
        - {"detail": {"error": {"message": ...}}}
        - {"detail": "string message"}
        """
        try:
            body = response.json()
        except (ValueError, httpx.ResponseNotRead):
            return HTTPError(
                code=f"HTTP_{response.status_code}",
                message=f"HTTP {response.status_code}",
            )

        # Try {"error": {...}} format
        if "error" in body and isinstance(body["error"], dict):
            error_obj = body["error"]
            return HTTPError(
                code=error_obj.get("code", f"HTTP_{response.status_code}"),
                message=error_obj.get("message", str(response.status_code)),
                details=error_obj,
            )

        # Try {"detail": {"error": {...}}} format (FastAPI HTTPException)
        if "detail" in body:
            detail = body["detail"]
            if isinstance(detail, dict) and "error" in detail:
                error_obj = detail["error"]
                return HTTPError(
                    code=error_obj.get("code", f"HTTP_{response.status_code}"),
                    message=error_obj.get("message", str(response.status_code)),
                    details=error_obj,
                )
            if isinstance(detail, str):
                return HTTPError(
                    code=f"HTTP_{response.status_code}",
                    message=detail,
                )

        return HTTPError(
            code=f"HTTP_{response.status_code}",
            message=f"HTTP {response.status_code}",
            details=body,
        )
