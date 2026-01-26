"""Tests for the IESDS (Iterated Elimination of Strictly Dominated Strategies) plugin."""
import pytest

from app.core.registry import AnalysisResult
from app.core.strategies import enumerate_strategies, resolve_payoffs
from app.core.gambit_utils import normal_form_to_gambit
from app.models.extensive_form import Action, DecisionNode, ExtensiveFormGame, Outcome
from app.models.normal_form import NormalFormGame
from app.plugins.iesds import IESDSPlugin, PYGAMBIT_AVAILABLE


@pytest.fixture
def plugin() -> IESDSPlugin:
    return IESDSPlugin()


@pytest.fixture
def prisoners_dilemma_nfg() -> NormalFormGame:
    """Prisoner's Dilemma - D strictly dominates C for both players."""
    return NormalFormGame(
        id="pd-nfg",
        title="Prisoner's Dilemma",
        players=("Row", "Column"),
        strategies=(["Cooperate", "Defect"], ["Cooperate", "Defect"]),
        payoffs=[
            [(-1, -1), (-3, 0)],
            [(0, -3), (-2, -2)],
        ],
    )


@pytest.fixture
def prisoners_dilemma_efg() -> ExtensiveFormGame:
    """Prisoner's Dilemma in extensive form with information sets (simultaneous)."""
    return ExtensiveFormGame(
        id="pd-efg",
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
            "o_cc": Outcome(label="CC", payoffs={"P1": -1, "P2": -1}),
            "o_cd": Outcome(label="CD", payoffs={"P1": -3, "P2": 0}),
            "o_dc": Outcome(label="DC", payoffs={"P1": 0, "P2": -3}),
            "o_dd": Outcome(label="DD", payoffs={"P1": -2, "P2": -2}),
        },
    )


@pytest.fixture
def matching_pennies_nfg() -> NormalFormGame:
    """Matching Pennies - no dominated strategies."""
    return NormalFormGame(
        id="mp-nfg",
        title="Matching Pennies",
        players=("Matcher", "Mismatcher"),
        strategies=(["Heads", "Tails"], ["Heads", "Tails"]),
        payoffs=[
            [(1, -1), (-1, 1)],
            [(-1, 1), (1, -1)],
        ],
    )


@pytest.fixture
def dominated_game_nfg() -> NormalFormGame:
    """A game where one strategy is strictly dominated."""
    # Row player's "Bad" is dominated by "Good"
    return NormalFormGame(
        id="dominated-nfg",
        title="Dominated Strategy Game",
        players=("Row", "Column"),
        strategies=(["Good", "Bad"], ["Left", "Right"]),
        payoffs=[
            [(3, 1), (3, 1)],  # Good gives 3 regardless
            [(1, 1), (1, 1)],  # Bad gives 1 regardless - dominated!
        ],
    )


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestIESDSPlugin:
    def test_plugin_metadata(self, plugin: IESDSPlugin):
        assert plugin.name == "IESDS"
        assert plugin.continuous is True
        assert "extensive" in plugin.applicable_to
        assert "strategic" in plugin.applicable_to

    def test_can_run_with_pygambit(self, plugin: IESDSPlugin, prisoners_dilemma_nfg: NormalFormGame):
        assert plugin.can_run(prisoners_dilemma_nfg) is True

    def test_prisoners_dilemma_nfg_elimination(
        self, plugin: IESDSPlugin, prisoners_dilemma_nfg: NormalFormGame
    ):
        """In PD, Cooperate is dominated by Defect for both players."""
        result = plugin.run(prisoners_dilemma_nfg)
        assert isinstance(result, AnalysisResult)

        eliminated = result.details["eliminated"]
        surviving = result.details["surviving"]

        # Both players should have Cooperate eliminated
        eliminated_strategies = [(e["player"], e["strategy"]) for e in eliminated]
        assert ("Row", "Cooperate") in eliminated_strategies
        assert ("Column", "Cooperate") in eliminated_strategies

        # Only Defect should survive for both
        assert surviving["Row"] == ["Defect"]
        assert surviving["Column"] == ["Defect"]

    def test_prisoners_dilemma_efg_elimination(
        self, plugin: IESDSPlugin, prisoners_dilemma_efg: ExtensiveFormGame
    ):
        """EFG version should also eliminate C for both players."""
        result = plugin.run(prisoners_dilemma_efg)
        assert isinstance(result, AnalysisResult)

        eliminated = result.details["eliminated"]
        # Should eliminate strategies containing C
        assert len(eliminated) >= 2

    def test_matching_pennies_no_elimination(
        self, plugin: IESDSPlugin, matching_pennies_nfg: NormalFormGame
    ):
        """Matching Pennies has no dominated strategies."""
        result = plugin.run(matching_pennies_nfg)

        eliminated = result.details["eliminated"]
        surviving = result.details["surviving"]

        assert len(eliminated) == 0
        assert surviving["Matcher"] == ["Heads", "Tails"]
        assert surviving["Mismatcher"] == ["Heads", "Tails"]

    def test_single_dominated_strategy(
        self, plugin: IESDSPlugin, dominated_game_nfg: NormalFormGame
    ):
        """Should eliminate the strictly dominated strategy."""
        result = plugin.run(dominated_game_nfg)

        eliminated = result.details["eliminated"]
        surviving = result.details["surviving"]

        # Row's "Bad" should be eliminated
        row_eliminated = [e for e in eliminated if e["player"] == "Row"]
        assert len(row_eliminated) == 1
        assert row_eliminated[0]["strategy"] == "Bad"

        # Column has no dominated strategies
        col_eliminated = [e for e in eliminated if e["player"] == "Column"]
        assert len(col_eliminated) == 0

        assert surviving["Row"] == ["Good"]
        assert surviving["Column"] == ["Left", "Right"]

    def test_rounds_counted_correctly(
        self, plugin: IESDSPlugin, prisoners_dilemma_nfg: NormalFormGame
    ):
        """Should track elimination rounds."""
        result = plugin.run(prisoners_dilemma_nfg)

        # All eliminations happen in round 1 (simultaneous dominance)
        rounds = result.details["rounds"]
        assert rounds >= 1

    def test_summarize_no_eliminations(self, plugin: IESDSPlugin, matching_pennies_nfg: NormalFormGame):
        """Summary should indicate no dominated strategies."""
        result = plugin.run(matching_pennies_nfg)
        assert "No dominated strategies" in result.summary

    def test_summarize_with_eliminations(
        self, plugin: IESDSPlugin, prisoners_dilemma_nfg: NormalFormGame
    ):
        """Summary should indicate strategies were eliminated."""
        result = plugin.run(prisoners_dilemma_nfg)
        # Should mention elimination count or specific strategy
        assert "eliminated" in result.summary.lower() or "Eliminated" in result.summary


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestIESDSPluginInternals:
    def test_enumerate_strategies_efg(self, prisoners_dilemma_efg: ExtensiveFormGame):
        """Should enumerate strategies respecting information sets."""
        strategies = enumerate_strategies(prisoners_dilemma_efg)

        # P1 has 2 strategies (C or D at root)
        assert len(strategies["P1"]) == 2

        # P2 has 2 strategies (same action at both info set nodes)
        assert len(strategies["P2"]) == 2

    def test_strategy_consistency_in_info_sets(self,  prisoners_dilemma_efg: ExtensiveFormGame):
        """Strategies should assign same action to nodes in same info set."""
        strategies = enumerate_strategies(prisoners_dilemma_efg)

        for strategy in strategies["P2"]:
            # Both P2 nodes are in same info set, must have same action
            assert strategy["n_p2_c"] == strategy["n_p2_d"]

    def test_resolve_payoffs(self, plugin: IESDSPlugin, prisoners_dilemma_efg: ExtensiveFormGame):
        """Should correctly resolve payoffs for a strategy profile."""
        profile = {
            "P1": {"n_p1": "D"},
            "P2": {"n_p2_c": "C", "n_p2_d": "C"},
        }
        payoffs = resolve_payoffs(prisoners_dilemma_efg, profile)

        # P1 plays D, P2 plays C -> DC outcome
        assert payoffs["P1"] == 0
        assert payoffs["P2"] == -3

    def test_normal_form_to_gambit_conversion(self, prisoners_dilemma_nfg: NormalFormGame):
        """Should convert NormalFormGame to Gambit game correctly."""
        gambit_game = normal_form_to_gambit(prisoners_dilemma_nfg)

        assert gambit_game.title == "Prisoner's Dilemma"
        assert len(gambit_game.players) == 2
        assert gambit_game.players[0].label == "Row"
        assert gambit_game.players[1].label == "Column"


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestIESDSIterativeElimination:
    """Tests for multi-round elimination scenarios."""

    @pytest.fixture
    def iterated_dominance_game(self) -> NormalFormGame:
        """A game requiring multiple rounds of elimination.

        After eliminating Row's dominated strategy, Column's strategy becomes dominated.
        """
        # Row: A, B, C
        # Column: X, Y
        # A dominates C for Row
        # After C is eliminated, X dominates Y for Column
        return NormalFormGame(
            id="iterated",
            title="Iterated Dominance",
            players=("Row", "Column"),
            strategies=(["A", "B", "C"], ["X", "Y"]),
            payoffs=[
                [(4, 3), (2, 2)],  # A
                [(3, 1), (3, 4)],  # B
                [(1, 2), (1, 3)],  # C - dominated by A (and B)
            ],
        )

    def test_multi_round_elimination(
        self, plugin: IESDSPlugin, iterated_dominance_game: NormalFormGame
    ):
        """Should perform multiple rounds of elimination."""
        result = plugin.run(iterated_dominance_game)

        eliminated = result.details["eliminated"]
        # At minimum, C should be eliminated
        row_eliminated = [e["strategy"] for e in eliminated if e["player"] == "Row"]
        assert "C" in row_eliminated
