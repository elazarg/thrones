"""Tests for CFR and exploitability analysis."""

import sys

import pytest

# Skip all tests on Windows since OpenSpiel doesn't work there
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="OpenSpiel not available on Windows"
)


@pytest.fixture
def kuhn_poker_efg():
    """Kuhn Poker as an extensive-form game."""
    return {
        "id": "kuhn-poker",
        "title": "Kuhn Poker",
        "format_name": "extensive",
        "players": [
            {"name": "Player 1"},
            {"name": "Player 2"},
        ],
        "efg_content": """EFG 2 R "Kuhn Poker" { "Player 1" "Player 2" }
c "" 1 "" { "J" 1/3 "Q" 1/3 "K" 1/3 } 0
c "" 2 "" { "J" 1/2 "Q" 1/2 } 0
p "" 1 1 "" { "p" "b" } 0
p "" 2 1 "" { "p" "b" } 0
t "" 1 "p1:J p2:Q" { -1 1 }
t "" 2 "p1:J p2:Q" { 1 -1 }
t "" 3 "p1:J p2:Q" { -2 2 }
p "" 1 2 "" { "p" "b" } 0
p "" 2 2 "" { "p" "b" } 0
t "" 4 "p1:J p2:K" { -1 1 }
t "" 5 "p1:J p2:K" { 1 -1 }
t "" 6 "p1:J p2:K" { -2 2 }
""",
    }


@pytest.fixture
def simple_efg():
    """Simple extensive-form game for testing."""
    return {
        "id": "simple-efg",
        "title": "Simple Game",
        "format_name": "extensive",
        "players": [
            {"name": "Player 1"},
            {"name": "Player 2"},
        ],
        "efg_content": """EFG 2 R "Simple Game" { "Player 1" "Player 2" }
p "" 1 1 "" { "L" "R" } 0
p "" 2 1 "" { "l" "r" } 0
t "" 1 "Ll" { 3 3 }
t "" 2 "Lr" { 0 0 }
p "" 2 1 "" { "l" "r" } 0
t "" 3 "Rl" { 0 0 }
t "" 4 "Rr" { 1 1 }
""",
    }


class TestCfrEquilibrium:
    def test_returns_valid_result(self, simple_efg):
        """Test that CFR returns a valid structure."""
        from openspiel_plugin.cfr import run_cfr_equilibrium

        result = run_cfr_equilibrium(simple_efg, {"iterations": 100})

        assert "summary" in result
        assert "details" in result

    def test_supports_algorithm_variants(self, simple_efg):
        """Test different CFR algorithm variants."""
        from openspiel_plugin.cfr import run_cfr_equilibrium

        for algo in ["cfr", "cfr+"]:
            result = run_cfr_equilibrium(
                simple_efg,
                {"iterations": 50, "algorithm": algo}
            )
            assert "summary" in result
            assert algo in result["details"].get("algorithm", "")

    def test_handles_missing_efg_content(self):
        """Test graceful handling of missing EFG content."""
        from openspiel_plugin.cfr import run_cfr_equilibrium

        result = run_cfr_equilibrium({"format_name": "extensive"}, {})

        assert "Error" in result["summary"]
        assert "error" in result["details"]


class TestExploitability:
    def test_returns_valid_result(self, simple_efg):
        """Test that exploitability returns a valid structure."""
        from openspiel_plugin.exploitability import run_exploitability

        result = run_exploitability(simple_efg, {})

        assert "summary" in result
        assert "details" in result
        assert "nash_conv" in result["details"]

    def test_exploitability_is_non_negative(self, simple_efg):
        """Test that exploitability is non-negative."""
        from openspiel_plugin.exploitability import run_exploitability

        result = run_exploitability(simple_efg, {})

        nash_conv = result["details"].get("nash_conv")
        if nash_conv is not None:
            assert nash_conv >= 0

    def test_handles_missing_efg_content(self):
        """Test graceful handling of missing EFG content."""
        from openspiel_plugin.exploitability import run_exploitability

        result = run_exploitability({"format_name": "extensive"}, {})

        assert "Error" in result["summary"]


class TestCfrConvergence:
    def test_returns_convergence_history(self, simple_efg):
        """Test that convergence tracking works."""
        from openspiel_plugin.exploitability import run_policy_exploitability

        result = run_policy_exploitability(
            simple_efg,
            {"iterations": 100}
        )

        assert "summary" in result
        assert "details" in result
        assert "convergence_history" in result["details"]
        assert "final_exploitability" in result["details"]

    def test_exploitability_decreases(self, simple_efg):
        """Test that exploitability generally decreases with iterations."""
        from openspiel_plugin.exploitability import run_policy_exploitability

        result = run_policy_exploitability(
            simple_efg,
            {"iterations": 500}
        )

        history = result["details"]["convergence_history"]
        if len(history) >= 2:
            # Later iterations should have lower exploitability
            assert history[-1]["exploitability"] <= history[0]["exploitability"]


class TestBestResponse:
    def test_returns_valid_result(self, simple_efg):
        """Test that best response returns a valid structure."""
        from openspiel_plugin.cfr import run_best_response

        result = run_best_response(simple_efg, {"player": 0})

        assert "summary" in result
        assert "details" in result

    def test_handles_missing_efg_content(self):
        """Test graceful handling of missing EFG content."""
        from openspiel_plugin.cfr import run_best_response

        result = run_best_response({"format_name": "extensive"}, {})

        assert "Error" in result["summary"]
