"""Tests for the dominance analysis plugin."""
import pytest

from app.core.registry import AnalysisResult
from app.core.strategies import enumerate_strategies, resolve_payoffs
from app.models.extensive_form import Action, DecisionNode, ExtensiveFormGame, Outcome
from app.plugins.dominance import DominancePlugin


@pytest.fixture
def plugin() -> DominancePlugin:
    return DominancePlugin()


@pytest.fixture
def trust_game() -> ExtensiveFormGame:
    """Trust game where Betray is dominated by Honor."""
    return ExtensiveFormGame(
        id="trust-game",
        title="Trust Game",
        players=["Alice", "Bob"],
        root="n_start",
        nodes={
            "n_start": DecisionNode(
                id="n_start",
                player="Alice",
                actions=[
                    Action(label="Trust", target="n_bob"),
                    Action(label="Don't", target="o_decline"),
                ],
            ),
            "n_bob": DecisionNode(
                id="n_bob",
                player="Bob",
                actions=[
                    Action(label="Honor", target="o_coop"),
                    Action(label="Betray", target="o_betray"),
                ],
            ),
        },
        outcomes={
            "o_coop": Outcome(label="Cooperate", payoffs={"Alice": 1, "Bob": 1}),
            "o_betray": Outcome(label="Betray", payoffs={"Alice": -1, "Bob": 2}),
            "o_decline": Outcome(label="Decline", payoffs={"Alice": 0, "Bob": 0}),
        },
    )


@pytest.fixture
def prisoners_dilemma() -> ExtensiveFormGame:
    """Prisoner's dilemma - no strictly dominated strategies in this form."""
    return ExtensiveFormGame(
        id="pd",
        title="Prisoner's Dilemma",
        players=["P1", "P2"],
        root="n_p1",
        nodes={
            "n_p1": DecisionNode(
                id="n_p1",
                player="P1",
                actions=[
                    Action(label="C", target="n_p2_c"),
                    Action(label="D", target="n_p2_d"),
                ],
            ),
            "n_p2_c": DecisionNode(
                id="n_p2_c",
                player="P2",
                information_set="h_p2",
                actions=[
                    Action(label="C", target="o_cc"),
                    Action(label="D", target="o_cd"),
                ],
            ),
            "n_p2_d": DecisionNode(
                id="n_p2_d",
                player="P2",
                information_set="h_p2",
                actions=[
                    Action(label="C", target="o_dc"),
                    Action(label="D", target="o_dd"),
                ],
            ),
        },
        outcomes={
            "o_cc": Outcome(label="CC", payoffs={"P1": 3, "P2": 3}),
            "o_cd": Outcome(label="CD", payoffs={"P1": 0, "P2": 5}),
            "o_dc": Outcome(label="DC", payoffs={"P1": 5, "P2": 0}),
            "o_dd": Outcome(label="DD", payoffs={"P1": 1, "P2": 1}),
        },
    )


class TestDominancePlugin:
    def test_plugin_metadata(self, plugin: DominancePlugin):
        assert plugin.name == "Dominance"
        assert plugin.continuous is True
        assert "extensive" in plugin.applicable_to

    def test_can_run_with_two_players(self, plugin: DominancePlugin, trust_game: ExtensiveFormGame):
        assert plugin.can_run(trust_game) is True

    def test_can_run_with_one_player(self, plugin: DominancePlugin):
        game = ExtensiveFormGame(
            id="one-player",
            title="One Player",
            players=["Solo"],
            root="n_solo",
            nodes={
                "n_solo": DecisionNode(
                    id="n_solo",
                    player="Solo",
                    actions=[Action(label="Go", target="o_end")],
                ),
            },
            outcomes={"o_end": Outcome(label="End", payoffs={"Solo": 1})},
        )
        assert plugin.can_run(game) is False

    def test_no_dominated_in_prisoners_dilemma(
        self, plugin: DominancePlugin, prisoners_dilemma: ExtensiveFormGame
    ):
        """In PD with simultaneous moves, D dominates C for both players."""
        result = plugin.run(prisoners_dilemma)
        assert isinstance(result, AnalysisResult)
        # D strictly dominates C in PD
        dominated = result.details["dominated_strategies"]
        # Should find that C is dominated for both players
        assert len(dominated) >= 1

    def test_summarize_no_dominated(self, plugin: DominancePlugin):
        result = AnalysisResult(summary="", details={"dominated_strategies": []})
        assert plugin.summarize(result) == "No dominated strategies"

    def test_summarize_one_dominated(self, plugin: DominancePlugin):
        result = AnalysisResult(
            summary="",
            details={
                "dominated_strategies": [
                    {"player": "Bob", "dominated": "Betray", "dominated_at_node": "n_bob"}
                ]
            },
        )
        summary = plugin.summarize(result)
        assert "Bob" in summary
        assert "Betray" in summary

    def test_summarize_multiple_dominated(self, plugin: DominancePlugin):
        result = AnalysisResult(
            summary="",
            details={
                "dominated_strategies": [
                    {"player": "P1", "dominated": "C", "dominated_at_node": "n_p1"},
                    {"player": "P2", "dominated": "C", "dominated_at_node": "n_p2"},
                ]
            },
        )
        summary = plugin.summarize(result)
        assert "2 dominated" in summary


class TestDominancePluginInternals:
    def test_enumerate_strategies(self, trust_game: ExtensiveFormGame):
        strategies = enumerate_strategies(trust_game)
        # Alice has 2 strategies at n_start
        assert len(strategies["Alice"]) == 2
        # Bob has 2 strategies at n_bob
        assert len(strategies["Bob"]) == 2

    def test_resolve_payoff(self, trust_game: ExtensiveFormGame):
        profile = {
            "Alice": {"n_start": "Trust"},
            "Bob": {"n_bob": "Honor"},
        }
        payoff = resolve_payoffs(trust_game, profile)
        assert payoff == {'Alice': 1.0, 'Bob': 1.0}


class TestDominanceInformationSets:
    """Tests for information set handling in dominance analysis."""

    @pytest.fixture
    def matching_pennies(self) -> ExtensiveFormGame:
        """Matching Pennies - P2 cannot see P1's choice."""
        return ExtensiveFormGame(
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
                    information_set="h_p2",
                    actions=[
                        Action(label="Heads", target="o_hh"),
                        Action(label="Tails", target="o_ht"),
                    ],
                ),
                "n_p2_after_tails": DecisionNode(
                    id="n_p2_after_tails",
                    player="P2",
                    information_set="h_p2",
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

    def test_info_set_strategy_enumeration(self, matching_pennies: ExtensiveFormGame):
        """P2 should have 2 strategies, not 4, due to information set."""
        strategies = enumerate_strategies(matching_pennies)
        # P1 has 2 strategies
        assert len(strategies["P1"]) == 2
        # P2 has only 2 strategies due to info set
        assert len(strategies["P2"]) == 2

    def test_info_set_strategy_consistency(self, matching_pennies: ExtensiveFormGame):
        """Each P2 strategy should assign same action to both nodes in info set."""
        strategies = enumerate_strategies(matching_pennies)
        for strategy in strategies["P2"]:
            assert strategy["n_p2_after_heads"] == strategy["n_p2_after_tails"]

    def test_matching_pennies_no_dominated(
        self, plugin: DominancePlugin, matching_pennies: ExtensiveFormGame
    ):
        """Matching Pennies has no dominated strategies when info sets are respected."""
        result = plugin.run(matching_pennies)
        # With proper info set handling, neither Heads nor Tails dominates
        # because each wins half the time
        dominated = result.details["dominated_strategies"]
        assert len(dominated) == 0

    def test_prisoners_dilemma_with_info_sets(self, prisoners_dilemma: ExtensiveFormGame):
        """PD should still find D dominates C even with info sets."""
        strategies = enumerate_strategies(prisoners_dilemma)
        # P2 has 2 nodes in same info set, so only 2 strategies
        assert len(strategies["P2"]) == 2
        # Each strategy should have same action at both P2 nodes
        for strategy in strategies["P2"]:
            assert strategy["n_p2_c"] == strategy["n_p2_d"]
