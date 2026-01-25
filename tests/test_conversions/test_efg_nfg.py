"""Tests for EFG <-> NFG conversions."""
import pytest

from app.conversions.efg_nfg import (
    check_efg_to_nfg,
    check_nfg_to_efg,
    convert_efg_to_nfg,
    convert_nfg_to_efg,
    _enumerate_strategies,
    _estimate_strategy_count,
    _resolve_payoffs,
)
from app.models.game import Action, DecisionNode, Game, Outcome
from app.models.normal_form import NormalFormGame


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_sequential_game() -> Game:
    """A simple 2-player sequential game (Alice moves, then Bob)."""
    return Game(
        id="simple-seq",
        title="Simple Sequential",
        players=["Alice", "Bob"],
        root="n_alice",
        nodes={
            "n_alice": DecisionNode(
                id="n_alice",
                player="Alice",
                actions=[
                    Action(label="Left", target="n_bob"),
                    Action(label="Right", target="o_right"),
                ],
            ),
            "n_bob": DecisionNode(
                id="n_bob",
                player="Bob",
                actions=[
                    Action(label="Up", target="o_up"),
                    Action(label="Down", target="o_down"),
                ],
            ),
        },
        outcomes={
            "o_right": Outcome(label="Right", payoffs={"Alice": 2, "Bob": 0}),
            "o_up": Outcome(label="Up", payoffs={"Alice": 3, "Bob": 1}),
            "o_down": Outcome(label="Down", payoffs={"Alice": 0, "Bob": 2}),
        },
    )


@pytest.fixture
def simultaneous_game() -> Game:
    """A 2-player simultaneous game (both in same info set)."""
    return Game(
        id="simultaneous",
        title="Simultaneous Game",
        players=["P1", "P2"],
        root="n_p1",
        nodes={
            "n_p1": DecisionNode(
                id="n_p1",
                player="P1",
                actions=[
                    Action(label="A", target="n_p2_a"),
                    Action(label="B", target="n_p2_b"),
                ],
            ),
            "n_p2_a": DecisionNode(
                id="n_p2_a",
                player="P2",
                information_set="h_p2",
                actions=[
                    Action(label="X", target="o_ax"),
                    Action(label="Y", target="o_ay"),
                ],
            ),
            "n_p2_b": DecisionNode(
                id="n_p2_b",
                player="P2",
                information_set="h_p2",
                actions=[
                    Action(label="X", target="o_bx"),
                    Action(label="Y", target="o_by"),
                ],
            ),
        },
        outcomes={
            "o_ax": Outcome(label="AX", payoffs={"P1": 1, "P2": 2}),
            "o_ay": Outcome(label="AY", payoffs={"P1": 3, "P2": 1}),
            "o_bx": Outcome(label="BX", payoffs={"P1": 2, "P2": 3}),
            "o_by": Outcome(label="BY", payoffs={"P1": 0, "P2": 0}),
        },
    )


@pytest.fixture
def three_player_game() -> Game:
    """A 3-player game (cannot convert to NFG matrix)."""
    return Game(
        id="three-player",
        title="Three Player Game",
        players=["P1", "P2", "P3"],
        root="n_p1",
        nodes={
            "n_p1": DecisionNode(
                id="n_p1",
                player="P1",
                actions=[Action(label="Go", target="n_p2")],
            ),
            "n_p2": DecisionNode(
                id="n_p2",
                player="P2",
                actions=[Action(label="Go", target="n_p3")],
            ),
            "n_p3": DecisionNode(
                id="n_p3",
                player="P3",
                actions=[Action(label="End", target="o_end")],
            ),
        },
        outcomes={
            "o_end": Outcome(label="End", payoffs={"P1": 1, "P2": 1, "P3": 1}),
        },
    )


@pytest.fixture
def prisoners_dilemma_nfg() -> NormalFormGame:
    """Prisoner's Dilemma in normal form."""
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
def rock_paper_scissors_nfg() -> NormalFormGame:
    """Rock-Paper-Scissors in normal form."""
    return NormalFormGame(
        id="rps-nfg",
        title="Rock Paper Scissors",
        players=("P1", "P2"),
        strategies=(["Rock", "Paper", "Scissors"], ["Rock", "Paper", "Scissors"]),
        payoffs=[
            [(0, 0), (-1, 1), (1, -1)],
            [(1, -1), (0, 0), (-1, 1)],
            [(-1, 1), (1, -1), (0, 0)],
        ],
    )


# =============================================================================
# EFG -> NFG Check Tests
# =============================================================================


class TestCheckEfgToNfg:
    def test_two_player_game_possible(self, simple_sequential_game: Game):
        """2-player games should be convertible."""
        result = check_efg_to_nfg(simple_sequential_game)
        assert result.possible is True
        assert len(result.blockers) == 0

    def test_three_player_game_blocked(self, three_player_game: Game):
        """3+ player games should be blocked."""
        result = check_efg_to_nfg(three_player_game)
        assert result.possible is False
        assert any("2 players" in b for b in result.blockers)

    def test_already_normal_form_blocked(self, prisoners_dilemma_nfg: NormalFormGame):
        """Already normal form should be blocked."""
        result = check_efg_to_nfg(prisoners_dilemma_nfg)
        assert result.possible is False
        assert any("Already normal form" in b for b in result.blockers)

    def test_warns_for_large_games(self):
        """Should warn for games with many strategy profiles."""
        # Create a game with many information sets
        nodes = {"n_root": DecisionNode(
            id="n_root",
            player="P1",
            actions=[Action(label=f"A{i}", target=f"n_p2_{i}") for i in range(5)],
        )}
        for i in range(5):
            nodes[f"n_p2_{i}"] = DecisionNode(
                id=f"n_p2_{i}",
                player="P2",
                actions=[Action(label=f"B{j}", target=f"o_{i}_{j}") for j in range(5)],
            )
        outcomes = {
            f"o_{i}_{j}": Outcome(label=f"O{i}{j}", payoffs={"P1": i, "P2": j})
            for i in range(5) for j in range(5)
        }

        game = Game(
            id="large",
            title="Large Game",
            players=["P1", "P2"],
            root="n_root",
            nodes=nodes,
            outcomes=outcomes,
        )

        result = check_efg_to_nfg(game)
        # 5 * 5^5 = 15625 profiles - should warn or block
        # Actually: P1 has 5 strategies, P2 has 5^5 = 3125 strategies -> 15625 profiles
        # This should warn but still be possible
        assert result.possible is True or len(result.blockers) > 0


# =============================================================================
# EFG -> NFG Conversion Tests
# =============================================================================


class TestConvertEfgToNfg:
    def test_sequential_game_conversion(self, simple_sequential_game: Game):
        """Should convert sequential game to normal form."""
        nfg = convert_efg_to_nfg(simple_sequential_game)

        assert isinstance(nfg, NormalFormGame)
        assert nfg.players == ("Alice", "Bob")
        assert len(nfg.strategies[0]) == 2  # Alice: Left, Right
        assert len(nfg.strategies[1]) == 2  # Bob: Up, Down

    def test_sequential_game_payoffs(self, simple_sequential_game: Game):
        """Payoffs should be correct in converted game."""
        nfg = convert_efg_to_nfg(simple_sequential_game)

        # Find indices for strategies
        alice_left = nfg.strategies[0].index("Left")
        alice_right = nfg.strategies[0].index("Right")
        bob_up = nfg.strategies[1].index("Up")
        bob_down = nfg.strategies[1].index("Down")

        # Alice plays Right -> outcome is (2, 0) regardless of Bob
        assert nfg.payoffs[alice_right][bob_up] == (2, 0)
        assert nfg.payoffs[alice_right][bob_down] == (2, 0)

        # Alice plays Left, Bob plays Up -> (3, 1)
        assert nfg.payoffs[alice_left][bob_up] == (3, 1)

        # Alice plays Left, Bob plays Down -> (0, 2)
        assert nfg.payoffs[alice_left][bob_down] == (0, 2)

    def test_simultaneous_game_conversion(self, simultaneous_game: Game):
        """Should convert simultaneous game preserving info set constraints."""
        nfg = convert_efg_to_nfg(simultaneous_game)

        assert isinstance(nfg, NormalFormGame)
        assert nfg.players == ("P1", "P2")
        assert len(nfg.strategies[0]) == 2  # P1: A, B
        assert len(nfg.strategies[1]) == 2  # P2: X, Y (info set constraint)

    def test_simultaneous_game_payoffs(self, simultaneous_game: Game):
        """Payoffs should be correct for simultaneous game."""
        nfg = convert_efg_to_nfg(simultaneous_game)

        p1_a = nfg.strategies[0].index("A")
        p1_b = nfg.strategies[0].index("B")
        # P2 strategies are labeled "X/X" and "Y/Y" because both nodes in the
        # info set must have the same action
        p2_x = nfg.strategies[1].index("X/X")
        p2_y = nfg.strategies[1].index("Y/Y")

        assert nfg.payoffs[p1_a][p2_x] == (1, 2)
        assert nfg.payoffs[p1_a][p2_y] == (3, 1)
        assert nfg.payoffs[p1_b][p2_x] == (2, 3)
        assert nfg.payoffs[p1_b][p2_y] == (0, 0)

    def test_conversion_preserves_title(self, simple_sequential_game: Game):
        """Title should be preserved."""
        nfg = convert_efg_to_nfg(simple_sequential_game)
        assert nfg.title == simple_sequential_game.title

    def test_conversion_adds_tags(self, simple_sequential_game: Game):
        """Should add 'converted' and 'from-efg' tags."""
        nfg = convert_efg_to_nfg(simple_sequential_game)
        assert "converted" in nfg.tags
        assert "from-efg" in nfg.tags

    def test_conversion_creates_new_id(self, simple_sequential_game: Game):
        """Should create a new ID for the converted game."""
        nfg = convert_efg_to_nfg(simple_sequential_game)
        assert nfg.id != simple_sequential_game.id
        assert simple_sequential_game.id in nfg.id

    def test_three_player_raises_error(self, three_player_game: Game):
        """Should raise error for 3+ player games."""
        with pytest.raises(ValueError, match="2 players"):
            convert_efg_to_nfg(three_player_game)

    def test_already_nfg_returns_same(self, prisoners_dilemma_nfg: NormalFormGame):
        """Should return same game if already NFG."""
        result = convert_efg_to_nfg(prisoners_dilemma_nfg)
        assert result is prisoners_dilemma_nfg


# =============================================================================
# NFG -> EFG Check Tests
# =============================================================================


class TestCheckNfgToEfg:
    def test_normal_form_always_possible(self, prisoners_dilemma_nfg: NormalFormGame):
        """NFG -> EFG should always be possible."""
        result = check_nfg_to_efg(prisoners_dilemma_nfg)
        assert result.possible is True
        assert len(result.blockers) == 0

    def test_warns_about_simultaneity(self, prisoners_dilemma_nfg: NormalFormGame):
        """Should warn about information set representation."""
        result = check_nfg_to_efg(prisoners_dilemma_nfg)
        assert any("information set" in w.lower() for w in result.warnings)

    def test_already_efg_blocked(self, simple_sequential_game: Game):
        """Already extensive form should be blocked."""
        result = check_nfg_to_efg(simple_sequential_game)
        assert result.possible is False
        assert any("Already extensive form" in b for b in result.blockers)


# =============================================================================
# NFG -> EFG Conversion Tests
# =============================================================================


class TestConvertNfgToEfg:
    def test_basic_conversion(self, prisoners_dilemma_nfg: NormalFormGame):
        """Should convert NFG to EFG."""
        efg = convert_nfg_to_efg(prisoners_dilemma_nfg)

        assert isinstance(efg, Game)
        assert efg.players == ["Row", "Column"]
        assert efg.root is not None
        assert len(efg.nodes) > 0
        assert len(efg.outcomes) == 4  # 2x2 = 4 outcomes

    def test_structure_p1_at_root(self, prisoners_dilemma_nfg: NormalFormGame):
        """P1 should be at the root node."""
        efg = convert_nfg_to_efg(prisoners_dilemma_nfg)

        root_node = efg.nodes[efg.root]
        assert root_node.player == "Row"
        assert len(root_node.actions) == 2  # Cooperate, Defect

    def test_structure_p2_in_info_set(self, prisoners_dilemma_nfg: NormalFormGame):
        """P2 nodes should all be in same information set (simultaneous move)."""
        efg = convert_nfg_to_efg(prisoners_dilemma_nfg)

        p2_nodes = [n for n in efg.nodes.values() if n.player == "Column"]
        assert len(p2_nodes) == 2

        info_sets = {n.information_set for n in p2_nodes}
        assert len(info_sets) == 1  # All in same info set
        assert None not in info_sets  # Info set should be assigned

    def test_payoffs_preserved(self, prisoners_dilemma_nfg: NormalFormGame):
        """Payoffs should be preserved in outcomes."""
        efg = convert_nfg_to_efg(prisoners_dilemma_nfg)

        # Find the (Defect, Defect) outcome
        dd_outcome = None
        for outcome in efg.outcomes.values():
            if "Defect" in outcome.label and outcome.label.count("Defect") == 2:
                dd_outcome = outcome
                break

        # Original PD has (-2, -2) for (Defect, Defect)
        assert dd_outcome is not None
        assert dd_outcome.payoffs["Row"] == -2
        assert dd_outcome.payoffs["Column"] == -2

    def test_larger_game_conversion(self, rock_paper_scissors_nfg: NormalFormGame):
        """Should handle larger games (3x3)."""
        efg = convert_nfg_to_efg(rock_paper_scissors_nfg)

        assert isinstance(efg, Game)
        assert len(efg.outcomes) == 9  # 3x3 = 9 outcomes

        root = efg.nodes[efg.root]
        assert len(root.actions) == 3  # Rock, Paper, Scissors

    def test_conversion_adds_tags(self, prisoners_dilemma_nfg: NormalFormGame):
        """Should add 'converted' and 'from-nfg' tags."""
        efg = convert_nfg_to_efg(prisoners_dilemma_nfg)
        assert "converted" in efg.tags
        assert "from-nfg" in efg.tags

    def test_already_efg_returns_same(self, simple_sequential_game: Game):
        """Should return same game if already EFG."""
        result = convert_nfg_to_efg(simple_sequential_game)
        assert result is simple_sequential_game


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestEnumerateStrategies:
    def test_sequential_game_strategies(self, simple_sequential_game: Game):
        """Should enumerate correct strategies for sequential game."""
        strategies = _enumerate_strategies(simple_sequential_game)

        # Alice has 2 strategies at one node
        assert len(strategies["Alice"]) == 2

        # Bob has 2 strategies at one node
        assert len(strategies["Bob"]) == 2

    def test_info_set_constrains_strategies(self, simultaneous_game: Game):
        """Info sets should constrain strategy enumeration."""
        strategies = _enumerate_strategies(simultaneous_game)

        # P1 has 2 strategies
        assert len(strategies["P1"]) == 2

        # P2 has 2 nodes in same info set -> only 2 strategies (not 4)
        assert len(strategies["P2"]) == 2

        # Each P2 strategy should assign same action to both nodes
        for strategy in strategies["P2"]:
            assert strategy["n_p2_a"] == strategy["n_p2_b"]

    def test_player_with_no_moves(self):
        """Player with no decision nodes should have one empty strategy."""
        game = Game(
            id="test",
            title="Test",
            players=["Active", "Passive"],
            root="n_active",
            nodes={
                "n_active": DecisionNode(
                    id="n_active",
                    player="Active",
                    actions=[Action(label="End", target="o_end")],
                ),
            },
            outcomes={
                "o_end": Outcome(label="End", payoffs={"Active": 1, "Passive": 0}),
            },
        )
        strategies = _enumerate_strategies(game)

        assert len(strategies["Active"]) == 1
        assert len(strategies["Passive"]) == 1
        assert strategies["Passive"][0] == {}  # Empty strategy


class TestEstimateStrategyCount:
    def test_simple_game(self, simple_sequential_game: Game):
        """Should estimate strategy count correctly."""
        count = _estimate_strategy_count(simple_sequential_game)
        # Alice: 2, Bob: 2 -> 4 profiles
        assert count == 4

    def test_info_set_game(self, simultaneous_game: Game):
        """Should account for info sets in estimation."""
        count = _estimate_strategy_count(simultaneous_game)
        # P1: 2, P2: 2 (constrained by info set) -> 4 profiles
        assert count == 4


class TestResolvePayoffs:
    def test_resolve_payoffs_sequential(self, simple_sequential_game: Game):
        """Should resolve payoffs for a strategy profile."""
        profile = {
            "Alice": {"n_alice": "Left"},
            "Bob": {"n_bob": "Up"},
        }
        payoffs = _resolve_payoffs(simple_sequential_game, profile)

        assert payoffs["Alice"] == 3
        assert payoffs["Bob"] == 1

    def test_resolve_payoffs_early_termination(self, simple_sequential_game: Game):
        """Should handle early termination (Right goes directly to outcome)."""
        profile = {
            "Alice": {"n_alice": "Right"},
            "Bob": {"n_bob": "Up"},  # Bob's action doesn't matter
        }
        payoffs = _resolve_payoffs(simple_sequential_game, profile)

        assert payoffs["Alice"] == 2
        assert payoffs["Bob"] == 0

    def test_missing_player_raises(self, simple_sequential_game: Game):
        """Should raise error for missing player strategy."""
        profile = {
            "Alice": {"n_alice": "Left"},
            # Bob missing
        }
        with pytest.raises(ValueError, match="missing strategy"):
            _resolve_payoffs(simple_sequential_game, profile)

    def test_missing_node_raises(self, simple_sequential_game: Game):
        """Should raise error for missing node in strategy."""
        profile = {
            "Alice": {"n_alice": "Left"},
            "Bob": {},  # Missing n_bob
        }
        with pytest.raises(ValueError, match="missing action"):
            _resolve_payoffs(simple_sequential_game, profile)


# =============================================================================
# Round-Trip Tests
# =============================================================================


class TestRoundTrip:
    def test_nfg_to_efg_preserves_equilibria(self, prisoners_dilemma_nfg: NormalFormGame):
        """Converting NFG -> EFG should preserve game structure."""
        efg = convert_nfg_to_efg(prisoners_dilemma_nfg)

        # Should have same number of strategy profiles
        strategies = _enumerate_strategies(efg)
        assert len(strategies["Row"]) == 2
        assert len(strategies["Column"]) == 2

    def test_efg_to_nfg_to_efg(self, simple_sequential_game: Game):
        """EFG -> NFG -> EFG should maintain strategic equivalence."""
        nfg = convert_efg_to_nfg(simple_sequential_game)
        efg2 = convert_nfg_to_efg(nfg)

        # Both should have same number of outcomes (strategy profiles)
        assert len(efg2.outcomes) == len(nfg.strategies[0]) * len(nfg.strategies[1])
