"""Tests for the remote plugin HTTP adapter."""
from __future__ import annotations

import threading
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.http_client import RemoteServiceClient
from app.core.remote_plugin import RemotePlugin
from app.core.registry import AnalysisResult


@pytest.fixture
def analysis_info() -> dict[str, Any]:
    """Sample analysis info as returned by /info endpoint."""
    return {
        "name": "Nash Equilibrium",
        "description": "Computes Nash equilibria using Gambit solvers.",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {
            "solver": {"type": "string", "enum": ["exhaustive", "quick"]},
        },
    }


@pytest.fixture
def remote_plugin(analysis_info) -> RemotePlugin:
    return RemotePlugin(base_url="http://127.0.0.1:9999", analysis_info=analysis_info)


class TestRemotePluginInit:
    def test_attributes(self, remote_plugin):
        assert remote_plugin.name == "Nash Equilibrium"
        assert remote_plugin.description == "Computes Nash equilibria using Gambit solvers."
        assert remote_plugin.applicable_to == ("extensive", "normal")
        assert remote_plugin.continuous is True
        assert remote_plugin.base_url == "http://127.0.0.1:9999"

    def test_non_continuous(self):
        info = {
            "name": "Verify Profile",
            "applicable_to": ["extensive"],
            "continuous": False,
        }
        plugin = RemotePlugin(base_url="http://localhost:1234", analysis_info=info)
        assert plugin.continuous is False


class TestCanRun:
    def test_can_run_matching_format(self, remote_plugin):
        game = MagicMock()
        game.format_name = "extensive"
        assert remote_plugin.can_run(game) is True

    def test_can_run_non_matching_format(self, remote_plugin):
        game = MagicMock()
        game.format_name = "maid"
        assert remote_plugin.can_run(game) is False

    def test_can_run_no_format(self, remote_plugin):
        game = MagicMock(spec=[])  # No format_name attribute
        assert remote_plugin.can_run(game) is False


class TestRunUnreachable:
    def test_unreachable_plugin(self, remote_plugin):
        """When plugin is not running, run() should return an error result."""
        game = MagicMock()
        game.id = "test-game"
        game.format_name = "extensive"
        game.model_dump.return_value = {"id": "test", "format_name": "extensive"}

        # Mock the store to return the game
        mock_store = MagicMock()
        mock_store.get_converted.return_value = game

        with patch("app.dependencies.get_game_store", return_value=mock_store):
            result = remote_plugin.run(game)
            assert isinstance(result, AnalysisResult)
            assert "unreachable" in result.summary.lower() or "error" in result.summary.lower()


class TestSummarize:
    def test_summarize(self, remote_plugin):
        result = AnalysisResult(summary="2 Nash equilibria", details={})
        assert remote_plugin.summarize(result) == "2 Nash equilibria"


class TestRunWithCancellation:
    def test_cancel_before_poll(self, remote_plugin):
        """If cancel_event is set, run should return cancelled result."""
        game = MagicMock()
        game.id = "test-game"
        game.format_name = "extensive"
        game.model_dump.return_value = {"id": "test", "format_name": "extensive"}

        cancel_event = threading.Event()

        # Mock the store to return the game
        mock_store = MagicMock()
        mock_store.get_converted.return_value = game

        # Mock httpx in http_client module
        with patch("app.core.http_client.httpx") as mock_httpx, \
             patch("app.dependencies.get_game_store", return_value=mock_store):

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"task_id": "p-abc", "status": "running"}
            mock_response.raise_for_status = MagicMock()
            mock_httpx.post.return_value = mock_response

            # Mock GET /tasks to return running, but cancel is set
            mock_poll = MagicMock()
            mock_poll.status_code = 200
            mock_poll.json.return_value = {"task_id": "p-abc", "status": "running"}
            mock_poll.raise_for_status = MagicMock()
            mock_httpx.get.return_value = mock_poll

            cancel_event.set()  # Pre-cancel

            result = remote_plugin.run(game, config={"_cancel_event": cancel_event})
            assert "cancelled" in result.summary.lower() or result.details.get("cancelled") is True


class TestStatusNormalization:
    """Tests for plugin status normalization in RemoteServiceClient."""

    def test_normalize_queued_to_pending(self):
        """Plugin 'queued' status should be normalized to 'pending'."""
        client = RemoteServiceClient("http://localhost:9999", "test")
        task = {"task_id": "123", "status": "queued"}
        normalized = client._normalize_task_status(task)
        assert normalized["status"] == "pending"

    def test_normalize_done_to_completed(self):
        """Plugin 'done' status should be normalized to 'completed'."""
        client = RemoteServiceClient("http://localhost:9999", "test")
        task = {"task_id": "123", "status": "done"}
        normalized = client._normalize_task_status(task)
        assert normalized["status"] == "completed"

    def test_running_unchanged(self):
        """'running' status should remain unchanged."""
        client = RemoteServiceClient("http://localhost:9999", "test")
        task = {"task_id": "123", "status": "running"}
        normalized = client._normalize_task_status(task)
        assert normalized["status"] == "running"

    def test_failed_unchanged(self):
        """'failed' status should remain unchanged."""
        client = RemoteServiceClient("http://localhost:9999", "test")
        task = {"task_id": "123", "status": "failed"}
        normalized = client._normalize_task_status(task)
        assert normalized["status"] == "failed"

    def test_cancelled_unchanged(self):
        """'cancelled' status should remain unchanged."""
        client = RemoteServiceClient("http://localhost:9999", "test")
        task = {"task_id": "123", "status": "cancelled"}
        normalized = client._normalize_task_status(task)
        assert normalized["status"] == "cancelled"

    def test_normalization_does_not_mutate_original(self):
        """Status normalization should not mutate the original task dict."""
        client = RemoteServiceClient("http://localhost:9999", "test")
        task = {"task_id": "123", "status": "queued"}
        normalized = client._normalize_task_status(task)
        assert task["status"] == "queued"  # Original unchanged
        assert normalized["status"] == "pending"  # Normalized copy

    def test_unknown_status_unchanged(self):
        """Unknown status values should pass through unchanged."""
        client = RemoteServiceClient("http://localhost:9999", "test")
        task = {"task_id": "123", "status": "unknown_status"}
        normalized = client._normalize_task_status(task)
        assert normalized["status"] == "unknown_status"
