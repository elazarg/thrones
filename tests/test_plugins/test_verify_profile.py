"""Tests for the profile verification plugin."""
import pytest

from app.core.gambit_utils import normal_form_to_gambit
from app.models.extensive_form import Action, DecisionNode, ExtensiveFormGame, Outcome
from app.models.normal_form import NormalFormGame
from app.plugins.verify_profile import VerifyProfilePlugin, PYGAMBIT_AVAILABLE


@pytest.fixture
def plugin() -> VerifyProfilePlugin:
    return VerifyProfilePlugin()


@pytest.fixture
def matching_pennies_nfg() -> NormalFormGame:
    """Matching Pennies - unique mixed equilibrium at (0.5, 0.5)."""
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
def prisoners_dilemma_nfg() -> NormalFormGame:
    """Prisoner's Dilemma - unique equilibrium at (Defect, Defect)."""
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
def battle_of_sexes_nfg() -> NormalFormGame:
    """Battle of the Sexes - two pure equilibria and one mixed."""
    return NormalFormGame(
        id="bos-nfg",
        title="Battle of the Sexes",
        players=("Alice", "Bob"),
        strategies=(["Opera", "Football"], ["Opera", "Football"]),
        payoffs=[
            [(3, 2), (0, 0)],
            [(0, 0), (2, 3)],
        ],
    )


@pytest.fixture
def trust_game_efg() -> ExtensiveFormGame:
    """Trust Game in extensive form."""
    return ExtensiveFormGame(
        id="trust-efg",
        title="Trust Game",
        players=["Alice", "Bob"],
        root="n_alice",
        nodes={
            "n_alice": DecisionNode(
                id="n_alice",
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
                    Action(label="Honor", target="o_honor"),
                    Action(label="Betray", target="o_betray"),
                ],
            ),
        },
        outcomes={
            "o_honor": Outcome(label="Honor", payoffs={"Alice": 1, "Bob": 1}),
            "o_betray": Outcome(label="Betray", payoffs={"Alice": -1, "Bob": 2}),
            "o_decline": Outcome(label="Decline", payoffs={"Alice": 0, "Bob": 0}),
        },
    )


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestVerifyProfilePlugin:
    def test_plugin_metadata(self, plugin: VerifyProfilePlugin):
        assert plugin.name == "Verify Profile"
        assert plugin.continuous is False  # Only runs with explicit config
        assert "extensive" in plugin.applicable_to
        assert "strategic" in plugin.applicable_to

    def test_can_run_with_pygambit(self, plugin: VerifyProfilePlugin, matching_pennies_nfg: NormalFormGame):
        assert plugin.can_run(matching_pennies_nfg) is True

    def test_requires_profile_config(self, plugin: VerifyProfilePlugin, matching_pennies_nfg: NormalFormGame):
        """Should raise error if no profile provided."""
        with pytest.raises(ValueError, match="profile"):
            plugin.run(matching_pennies_nfg, config=None)

        with pytest.raises(ValueError, match="profile"):
            plugin.run(matching_pennies_nfg, config={})

    def test_verify_pure_equilibrium_pd(
        self, plugin: VerifyProfilePlugin, prisoners_dilemma_nfg: NormalFormGame
    ):
        """(Defect, Defect) is the unique Nash equilibrium in PD."""
        profile = {
            "Row": {"Cooperate": 0.0, "Defect": 1.0},
            "Column": {"Cooperate": 0.0, "Defect": 1.0},
        }
        result = plugin.run(prisoners_dilemma_nfg, config={"profile": profile})

        assert result.details["is_equilibrium"] is True
        assert result.details["max_regret"] < 1e-6
        assert "equilibrium" in result.summary.lower()

    def test_verify_non_equilibrium_pd(
        self, plugin: VerifyProfilePlugin, prisoners_dilemma_nfg: NormalFormGame
    ):
        """(Cooperate, Cooperate) is NOT an equilibrium - both want to deviate."""
        profile = {
            "Row": {"Cooperate": 1.0, "Defect": 0.0},
            "Column": {"Cooperate": 1.0, "Defect": 0.0},
        }
        result = plugin.run(prisoners_dilemma_nfg, config={"profile": profile})

        assert result.details["is_equilibrium"] is False
        assert result.details["max_regret"] > 0
        assert "not" in result.summary.lower() or "regret" in result.summary.lower()

    def test_verify_mixed_equilibrium_matching_pennies(
        self, plugin: VerifyProfilePlugin, matching_pennies_nfg: NormalFormGame
    ):
        """(0.5, 0.5) for both players is the unique mixed equilibrium."""
        profile = {
            "Matcher": {"Heads": 0.5, "Tails": 0.5},
            "Mismatcher": {"Heads": 0.5, "Tails": 0.5},
        }
        result = plugin.run(matching_pennies_nfg, config={"profile": profile})

        assert result.details["is_equilibrium"] is True
        assert result.details["max_regret"] < 1e-6

    def test_verify_non_equilibrium_mixed_matching_pennies(
        self, plugin: VerifyProfilePlugin, matching_pennies_nfg: NormalFormGame
    ):
        """Unbalanced mixed strategy is not an equilibrium."""
        profile = {
            "Matcher": {"Heads": 0.7, "Tails": 0.3},
            "Mismatcher": {"Heads": 0.5, "Tails": 0.5},
        }
        result = plugin.run(matching_pennies_nfg, config={"profile": profile})

        # Matcher's unbalanced strategy against 50-50 gives positive regret
        assert result.details["is_equilibrium"] is False

    def test_verify_pure_equilibrium_bos(
        self, plugin: VerifyProfilePlugin, battle_of_sexes_nfg: NormalFormGame
    ):
        """(Opera, Opera) is a pure Nash equilibrium in Battle of Sexes."""
        profile = {
            "Alice": {"Opera": 1.0, "Football": 0.0},
            "Bob": {"Opera": 1.0, "Football": 0.0},
        }
        result = plugin.run(battle_of_sexes_nfg, config={"profile": profile})

        assert result.details["is_equilibrium"] is True

    def test_verify_second_pure_equilibrium_bos(
        self, plugin: VerifyProfilePlugin, battle_of_sexes_nfg: NormalFormGame
    ):
        """(Football, Football) is also a pure Nash equilibrium."""
        profile = {
            "Alice": {"Opera": 0.0, "Football": 1.0},
            "Bob": {"Opera": 0.0, "Football": 1.0},
        }
        result = plugin.run(battle_of_sexes_nfg, config={"profile": profile})

        assert result.details["is_equilibrium"] is True

    def test_strategy_regrets_returned(
        self, plugin: VerifyProfilePlugin, prisoners_dilemma_nfg: NormalFormGame
    ):
        """Should return per-strategy regrets."""
        profile = {
            "Row": {"Cooperate": 1.0, "Defect": 0.0},
            "Column": {"Cooperate": 1.0, "Defect": 0.0},
        }
        result = plugin.run(prisoners_dilemma_nfg, config={"profile": profile})

        regrets = result.details["strategy_regrets"]
        assert "Row" in regrets
        assert "Column" in regrets
        assert "Cooperate" in regrets["Row"]
        assert "Defect" in regrets["Row"]

    def test_payoffs_returned(
        self, plugin: VerifyProfilePlugin, prisoners_dilemma_nfg: NormalFormGame
    ):
        """Should return expected payoffs for the profile."""
        profile = {
            "Row": {"Cooperate": 0.0, "Defect": 1.0},
            "Column": {"Cooperate": 0.0, "Defect": 1.0},
        }
        result = plugin.run(prisoners_dilemma_nfg, config={"profile": profile})

        payoffs = result.details["payoffs"]
        assert payoffs["Row"] == -2  # DD outcome
        assert payoffs["Column"] == -2


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestVerifyProfileExtensiveForm:
    """Tests for extensive form games."""

    def test_verify_equilibrium_efg(
        self, plugin: VerifyProfilePlugin, trust_game_efg: ExtensiveFormGame
    ):
        """Test verification on extensive form game."""
        # (Don't, Betray) is the subgame perfect equilibrium
        profile = {
            "Alice": {"Don't": 1.0, "Trust": 0.0},
            "Bob": {"Betray": 1.0, "Honor": 0.0},
        }
        result = plugin.run(trust_game_efg, config={"profile": profile})

        # This should be an equilibrium (backward induction solution)
        assert result.details["is_equilibrium"] is True

    def test_non_equilibrium_efg(
        self, plugin: VerifyProfilePlugin, trust_game_efg: ExtensiveFormGame
    ):
        """(Trust, Honor) is not an equilibrium - Bob wants to deviate."""
        profile = {
            "Alice": {"Trust": 1.0, "Don't": 0.0},
            "Bob": {"Honor": 1.0, "Betray": 0.0},
        }
        result = plugin.run(trust_game_efg, config={"profile": profile})

        # Bob would deviate to Betray for payoff 2 instead of 1
        assert result.details["is_equilibrium"] is False


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestVerifyProfileInternals:
    def test_clean_float(self, plugin: VerifyProfilePlugin):
        """Should clean floating point values."""
        assert plugin._clean_float(1e-12) == 0.0
        assert plugin._clean_float(0.5) == 0.5
        assert plugin._clean_float(0.123456789012345) == 0.1234567890

    def test_normal_form_to_gambit(
        self, matching_pennies_nfg: NormalFormGame
    ):
        """Should convert NormalFormGame to Gambit format."""
        gambit_game = normal_form_to_gambit(matching_pennies_nfg)

        assert gambit_game.title == "Matching Pennies"
        assert len(gambit_game.players) == 2
        assert len(gambit_game.players[0].strategies) == 2
        assert len(gambit_game.players[1].strategies) == 2
