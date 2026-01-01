"""Tests for Nash equilibrium plugin."""
from __future__ import annotations

import pytest

from app.core.registry import registry
from app.models.game import Action, DecisionNode, Game, Outcome


@pytest.fixture
def nash_plugin():
    """Get the Nash equilibrium plugin from registry."""
    plugin = registry.get_analysis("Nash Equilibrium")
    assert plugin is not None
    return plugin


class TestNashPlugin:
    def test_plugin_metadata(self, nash_plugin):
        assert nash_plugin.name == "Nash Equilibrium"
        assert nash_plugin.continuous is True
        assert "extensive" in nash_plugin.applicable_to

    def test_can_run(self, nash_plugin, trust_game: Game):
        # Should be True if pygambit is available
        result = nash_plugin.can_run(trust_game)
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_run_on_trust_game(self, nash_plugin, trust_game: Game):
        result = nash_plugin.run(trust_game)
        assert result.summary is not None
        assert "equilibria" in result.details
        equilibria = result.details["equilibria"]
        # Trust game should have at least 1 equilibrium
        assert len(equilibria) >= 1

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_equilibrium_structure(self, nash_plugin, trust_game: Game):
        result = nash_plugin.run(trust_game)
        eq = result.details["equilibria"][0]
        # Check structure
        assert "description" in eq
        assert "behavior_profile" in eq
        assert "outcomes" in eq
        assert "strategies" in eq
        assert "payoffs" in eq
        # Check players are in results
        assert "Alice" in eq["behavior_profile"]
        assert "Bob" in eq["behavior_profile"]

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_description_format(self, nash_plugin, trust_game: Game):
        result = nash_plugin.run(trust_game)
        for eq in result.details["equilibria"]:
            desc = eq["description"]
            # Should be either "Pure: ..." or "Mixed equilibrium"
            assert desc.startswith("Pure:") or desc == "Mixed equilibrium"

    def test_summarize(self, nash_plugin):
        from app.core.registry import AnalysisResult

        # Test with 0 equilibria
        result = AnalysisResult(summary="", details={"equilibria": []})
        assert nash_plugin.summarize(result) == "No Nash equilibria"

        # Test with 1 equilibrium
        result = AnalysisResult(summary="", details={"equilibria": [{}]})
        assert nash_plugin.summarize(result) == "1 Nash equilibrium (Gambit)"

        # Test with multiple equilibria
        result = AnalysisResult(summary="", details={"equilibria": [{}, {}]})
        assert nash_plugin.summarize(result) == "2 Nash equilibria (Gambit)"


class TestNashPluginInternals:
    """Test internal methods of Nash plugin."""

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_enumerate_strategies(self, nash_plugin, trust_game: Game):
        strategies = nash_plugin._enumerate_strategies(trust_game)
        assert "Alice" in strategies
        assert "Bob" in strategies
        # Alice has 2 actions at one node
        assert len(strategies["Alice"]) == 2
        # Bob has 2 actions at one node
        assert len(strategies["Bob"]) == 2

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_resolve_payoffs(self, nash_plugin, trust_game: Game):
        # Test Trust -> Honor path
        profile = {
            "Alice": {"n_start": "Trust"},
            "Bob": {"n_bob": "Honor"},
        }
        payoffs = nash_plugin._resolve_payoffs(trust_game, profile)
        assert payoffs == {"Alice": 1, "Bob": 1}

        # Test Don't path
        profile = {
            "Alice": {"n_start": "Don't"},
            "Bob": {"n_bob": "Honor"},
        }
        payoffs = nash_plugin._resolve_payoffs(trust_game, profile)
        assert payoffs == {"Alice": 0, "Bob": 0}

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_resolve_payoffs_invalid_profile(self, nash_plugin, trust_game: Game):
        # Missing player strategy
        profile = {"Alice": {"n_start": "Trust"}}
        with pytest.raises(ValueError, match="missing strategy"):
            nash_plugin._resolve_payoffs(trust_game, profile)
