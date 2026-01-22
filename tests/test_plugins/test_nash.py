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
        assert nash_plugin.summarize(result) == "No Nash equilibria found"

        # Test with 1 equilibrium (exhaustive)
        result = AnalysisResult(summary="", details={"equilibria": [{}]})
        assert nash_plugin.summarize(result, exhaustive=True) == "1 Nash equilibrium"

        # Test with multiple equilibria (exhaustive)
        result = AnalysisResult(summary="", details={"equilibria": [{}, {}]})
        assert nash_plugin.summarize(result, exhaustive=True) == "2 Nash equilibria"

        # Test with non-exhaustive search (adds + suffix)
        result = AnalysisResult(summary="", details={"equilibria": [{}]})
        assert nash_plugin.summarize(result, exhaustive=False) == "1 Nash equilibrium+"


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


class TestInformationSetHandling:
    """Tests specifically for information set handling."""

    @pytest.fixture
    def matching_pennies(self) -> Game:
        """Matching Pennies - P2 cannot see P1's choice (simultaneous move)."""
        return Game(
            id="matching-pennies",
            title="Matching Pennies",
            players=["P1", "P2"],
            root="n_p1",
            nodes={
                "n_p1": DecisionNode(
                    id="n_p1",
                    player="P1",
                    actions=[
                        Action(label="Heads", target="n_p2_after_heads"),
                        Action(label="Tails", target="n_p2_after_tails"),
                    ],
                ),
                "n_p2_after_heads": DecisionNode(
                    id="n_p2_after_heads",
                    player="P2",
                    information_set="h_p2",  # Same info set - can't distinguish
                    actions=[
                        Action(label="Heads", target="o_hh"),
                        Action(label="Tails", target="o_ht"),
                    ],
                ),
                "n_p2_after_tails": DecisionNode(
                    id="n_p2_after_tails",
                    player="P2",
                    information_set="h_p2",  # Same info set - can't distinguish
                    actions=[
                        Action(label="Heads", target="o_th"),
                        Action(label="Tails", target="o_tt"),
                    ],
                ),
            },
            outcomes={
                "o_hh": Outcome(label="HH", payoffs={"P1": 1, "P2": -1}),
                "o_ht": Outcome(label="HT", payoffs={"P1": -1, "P2": 1}),
                "o_th": Outcome(label="TH", payoffs={"P1": -1, "P2": 1}),
                "o_tt": Outcome(label="TT", payoffs={"P1": 1, "P2": -1}),
            },
        )

    @pytest.fixture
    def sequential_pennies(self) -> Game:
        """Pennies where P2 CAN see P1's choice (sequential move, no info set)."""
        return Game(
            id="sequential-pennies",
            title="Sequential Pennies",
            players=["P1", "P2"],
            root="n_p1",
            nodes={
                "n_p1": DecisionNode(
                    id="n_p1",
                    player="P1",
                    actions=[
                        Action(label="Heads", target="n_p2_after_heads"),
                        Action(label="Tails", target="n_p2_after_tails"),
                    ],
                ),
                "n_p2_after_heads": DecisionNode(
                    id="n_p2_after_heads",
                    player="P2",
                    # No information_set - can distinguish nodes
                    actions=[
                        Action(label="Heads", target="o_hh"),
                        Action(label="Tails", target="o_ht"),
                    ],
                ),
                "n_p2_after_tails": DecisionNode(
                    id="n_p2_after_tails",
                    player="P2",
                    # No information_set - can distinguish nodes
                    actions=[
                        Action(label="Heads", target="o_th"),
                        Action(label="Tails", target="o_tt"),
                    ],
                ),
            },
            outcomes={
                "o_hh": Outcome(label="HH", payoffs={"P1": 1, "P2": -1}),
                "o_ht": Outcome(label="HT", payoffs={"P1": -1, "P2": 1}),
                "o_th": Outcome(label="TH", payoffs={"P1": -1, "P2": 1}),
                "o_tt": Outcome(label="TT", payoffs={"P1": 1, "P2": -1}),
            },
        )

    def test_info_set_strategy_count(self, nash_plugin, matching_pennies: Game):
        """P2 should have 2 strategies, not 4, due to information set."""
        strategies = nash_plugin._enumerate_strategies(matching_pennies)
        # P1 has 2 strategies (Heads or Tails)
        assert len(strategies["P1"]) == 2
        # P2 has only 2 strategies due to info set (must choose same at both nodes)
        assert len(strategies["P2"]) == 2

    def test_no_info_set_strategy_count(self, nash_plugin, sequential_pennies: Game):
        """P2 should have 4 strategies when nodes are distinguishable."""
        strategies = nash_plugin._enumerate_strategies(sequential_pennies)
        # P1 has 2 strategies
        assert len(strategies["P1"]) == 2
        # P2 has 4 strategies (can choose independently at each node)
        assert len(strategies["P2"]) == 4

    def test_info_set_strategy_consistency(self, nash_plugin, matching_pennies: Game):
        """Each P2 strategy should assign same action to both nodes."""
        strategies = nash_plugin._enumerate_strategies(matching_pennies)
        for strategy in strategies["P2"]:
            # Both nodes in info set must have same action
            assert strategy["n_p2_after_heads"] == strategy["n_p2_after_tails"]

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_matching_pennies_mixed_equilibrium(self, nash_plugin, matching_pennies: Game):
        """Matching Pennies should have only a mixed equilibrium (50-50)."""
        result = nash_plugin.run(matching_pennies)
        equilibria = result.details["equilibria"]
        # Should find exactly one equilibrium
        assert len(equilibria) == 1
        eq = equilibria[0]
        # Should be mixed (not pure)
        assert eq["description"] == "Mixed equilibrium"
        # Payoffs should be 0 for both (expected value of mixed strategy)
        assert abs(eq["payoffs"]["P1"]) < 0.01
        assert abs(eq["payoffs"]["P2"]) < 0.01

    @pytest.mark.skipif(
        not registry.get_analysis("Nash Equilibrium").can_run(None),
        reason="pygambit not available",
    )
    def test_sequential_pennies_pure_equilibrium(self, nash_plugin, sequential_pennies: Game):
        """Sequential Pennies should have pure equilibria where P2 always wins."""
        result = nash_plugin.run(sequential_pennies)
        equilibria = result.details["equilibria"]
        # Should have equilibria
        assert len(equilibria) >= 1
        # In sequential version, P2 can always win by matching/not matching
        # Check that at least one equilibrium has P2 winning
        p2_wins = any(eq["payoffs"]["P2"] > 0 for eq in equilibria)
        assert p2_wins, "P2 should be able to win in sequential version"
