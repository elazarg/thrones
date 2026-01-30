"""Tests for replicator dynamics and evolutionary stability analysis."""

import pytest

from egttools_plugin.replicator import run_replicator_dynamics, nfg_to_payoff_matrix
from egttools_plugin.fixation import run_evolutionary_stability


@pytest.fixture
def prisoners_dilemma_nfg():
    """Prisoner's Dilemma as a normal-form game."""
    return {
        "id": "pd-nfg",
        "title": "Prisoner's Dilemma",
        "format_name": "normal",
        "players": ["Row", "Column"],
        "strategies": [["Cooperate", "Defect"], ["Cooperate", "Defect"]],
        "payoffs": [
            [[-1, -1], [-3, 0]],  # Row cooperates
            [[0, -3], [-2, -2]],  # Row defects
        ],
    }


@pytest.fixture
def hawk_dove_nfg():
    """Hawk-Dove game for evolutionary analysis."""
    return {
        "id": "hawk-dove",
        "title": "Hawk-Dove",
        "format_name": "normal",
        "players": ["Player 1", "Player 2"],
        "strategies": [["Hawk", "Dove"], ["Hawk", "Dove"]],
        "payoffs": [
            [[-1, -1], [2, 0]],  # Player 1 plays Hawk
            [[0, 2], [1, 1]],   # Player 1 plays Dove
        ],
    }


class TestNfgToPayoffMatrix:
    def test_converts_payoffs_correctly(self, prisoners_dilemma_nfg):
        """Test that payoff matrix extraction works."""
        matrix = nfg_to_payoff_matrix(prisoners_dilemma_nfg)

        assert matrix.shape == (2, 2)
        # Check player 1's payoffs
        assert matrix[0, 0] == -1  # (C, C)
        assert matrix[0, 1] == -3  # (C, D)
        assert matrix[1, 0] == 0   # (D, C)
        assert matrix[1, 1] == -2  # (D, D)

    def test_raises_on_empty_payoffs(self):
        """Test that missing payoffs raise an error."""
        with pytest.raises(ValueError, match="no payoffs"):
            nfg_to_payoff_matrix({"payoffs": []})


class TestReplicatorDynamics:
    def test_returns_valid_result(self, prisoners_dilemma_nfg):
        """Test that replicator dynamics returns a valid structure."""
        result = run_replicator_dynamics(prisoners_dilemma_nfg, {"time_steps": 50})

        assert "summary" in result
        assert "details" in result
        assert "trajectory" in result["details"]
        assert "times" in result["details"]
        assert "strategy_labels" in result["details"]

    def test_trajectory_has_correct_length(self, prisoners_dilemma_nfg):
        """Test that trajectory matches time_steps."""
        time_steps = 50
        result = run_replicator_dynamics(prisoners_dilemma_nfg, {"time_steps": time_steps})

        trajectory = result["details"]["trajectory"]
        assert len(trajectory) == time_steps + 1  # Includes initial state

    def test_frequencies_sum_to_one(self, prisoners_dilemma_nfg):
        """Test that strategy frequencies always sum to 1."""
        result = run_replicator_dynamics(prisoners_dilemma_nfg, {"time_steps": 100})

        trajectory = result["details"]["trajectory"]
        for state in trajectory:
            assert abs(sum(state) - 1.0) < 1e-6

    def test_pd_converges_to_defect(self, prisoners_dilemma_nfg):
        """Test that Prisoner's Dilemma converges to Defect."""
        result = run_replicator_dynamics(
            prisoners_dilemma_nfg,
            {"time_steps": 500, "initial_population": [0.5, 0.5]}
        )

        final_state = result["details"]["final_state"]
        # Defect should dominate (index 1)
        assert final_state[1] > 0.8

    def test_custom_initial_population(self, prisoners_dilemma_nfg):
        """Test that custom initial population is used."""
        initial = [0.8, 0.2]
        result = run_replicator_dynamics(
            prisoners_dilemma_nfg,
            {"time_steps": 10, "initial_population": initial}
        )

        initial_state = result["details"]["initial_state"]
        assert abs(initial_state[0] - 0.8) < 0.01
        assert abs(initial_state[1] - 0.2) < 0.01


class TestEvolutionaryStability:
    def test_returns_valid_result(self, prisoners_dilemma_nfg):
        """Test that evolutionary stability returns a valid structure."""
        result = run_evolutionary_stability(
            prisoners_dilemma_nfg,
            {"population_size": 50}
        )

        assert "summary" in result
        assert "details" in result
        assert "stationary_distribution" in result["details"]
        assert "strategy_labels" in result["details"]

    def test_stationary_distribution_sums_to_one(self, prisoners_dilemma_nfg):
        """Test that stationary distribution is valid."""
        result = run_evolutionary_stability(
            prisoners_dilemma_nfg,
            {"population_size": 50}
        )

        dist = result["details"]["stationary_distribution"]
        total = sum(dist.values())
        assert abs(total - 1.0) < 1e-6

    def test_pd_defect_dominates(self, prisoners_dilemma_nfg):
        """Test that Defect dominates or equals Cooperate in Prisoner's Dilemma."""
        result = run_evolutionary_stability(
            prisoners_dilemma_nfg,
            {"population_size": 100, "intensity_of_selection": 1.0}
        )

        dist = result["details"]["stationary_distribution"]
        # Defect should have at least equal frequency (dominant strategy)
        assert dist["Defect"] >= dist["Cooperate"]

    def test_handles_empty_game(self):
        """Test graceful handling of invalid input."""
        result = run_evolutionary_stability({}, {})

        assert "summary" in result
        # Should either error or return empty result
        assert "Error" in result["summary"] or "details" in result
