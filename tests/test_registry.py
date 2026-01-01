"""Tests for plugin registry."""
from __future__ import annotations

from app.core.registry import AnalysisResult, Registry, registry


class MockPlugin:
    """Mock analysis plugin for testing."""

    name = "Mock Analysis"
    description = "A mock plugin"
    applicable_to = ("extensive",)
    continuous = True

    def can_run(self, game):
        return True

    def run(self, game, config=None):
        return AnalysisResult(summary="Mock result", details={"test": True})

    def summarize(self, result):
        return result.summary


class TestAnalysisResult:
    def test_create_result(self):
        result = AnalysisResult(summary="Test", details={"key": "value"})
        assert result.summary == "Test"
        assert result.details == {"key": "value"}

    def test_result_allows_extra(self):
        # AnalysisResult has extra="allow"
        result = AnalysisResult(summary="Test", details={}, extra_field="allowed")
        assert hasattr(result, "extra_field")


class TestRegistry:
    def test_register_and_get_analysis(self):
        reg = Registry()
        plugin = MockPlugin()
        reg.register_analysis(plugin)
        assert reg.get_analysis("Mock Analysis") is plugin

    def test_get_nonexistent_analysis(self):
        reg = Registry()
        assert reg.get_analysis("Nonexistent") is None

    def test_analyses_iteration(self):
        reg = Registry()
        plugin1 = MockPlugin()
        plugin2 = MockPlugin()
        plugin2.name = "Another Mock"
        reg.register_analysis(plugin1)
        reg.register_analysis(plugin2)
        plugins = list(reg.analyses())
        assert len(plugins) == 2

    def test_global_registry_has_nash(self):
        # The global registry should have Nash plugin loaded
        nash = registry.get_analysis("Nash Equilibrium")
        assert nash is not None
        assert nash.name == "Nash Equilibrium"
