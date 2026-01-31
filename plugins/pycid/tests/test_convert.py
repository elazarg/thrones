"""Tests for MAID to EFG conversion."""

import pytest

from pycid_plugin.convert import convert_maid_to_efg


@pytest.fixture
def prisoners_dilemma_maid():
    """Prisoner's Dilemma as a MAID."""
    return {
        "id": "pd-maid",
        "title": "Prisoner's Dilemma",
        "format_name": "maid",
        "agents": ["Row", "Column"],
        "nodes": [
            {"id": "D1", "type": "decision", "agent": "Row", "domain": ["C", "D"]},
            {"id": "D2", "type": "decision", "agent": "Column", "domain": ["C", "D"]},
            {"id": "U1", "type": "utility", "agent": "Row", "domain": [-3, -2, -1, 0]},
            {
                "id": "U2",
                "type": "utility",
                "agent": "Column",
                "domain": [-3, -2, -1, 0],
            },
        ],
        "edges": [
            {"source": "D1", "target": "U1"},
            {"source": "D1", "target": "U2"},
            {"source": "D2", "target": "U1"},
            {"source": "D2", "target": "U2"},
        ],
        "cpds": [
            {
                "node": "U1",
                "parents": ["D1", "D2"],
                "values": [
                    [1.0, 0.0, 0.0, 0.0],  # -3: Row=C, Col=D
                    [0.0, 0.0, 0.0, 1.0],  # -2: Both D
                    [0.0, 1.0, 0.0, 0.0],  # -1: Both C
                    [0.0, 0.0, 1.0, 0.0],  # 0: Row=D, Col=C
                ],
            },
            {
                "node": "U2",
                "parents": ["D1", "D2"],
                "values": [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
            },
        ],
        "tags": ["maid", "2-player", "example"],
    }


def test_convert_maid_to_efg_returns_extensive_format(prisoners_dilemma_maid):
    """Test that conversion produces an extensive form game."""
    result = convert_maid_to_efg(prisoners_dilemma_maid)

    assert result["format_name"] == "extensive"
    assert "id" in result
    assert "title" in result
    assert "players" in result
    assert "root" in result
    assert "nodes" in result
    assert "outcomes" in result


def test_convert_maid_to_efg_preserves_players(prisoners_dilemma_maid):
    """Test that conversion preserves player names."""
    result = convert_maid_to_efg(prisoners_dilemma_maid)

    # The converted game should have the same agents as players
    players = result["players"]
    assert len(players) == 2
    assert "Row" in players or any("Row" in p for p in players)
    assert "Column" in players or any("Column" in p for p in players)


def test_convert_maid_to_efg_has_valid_tree_structure(prisoners_dilemma_maid):
    """Test that the converted game has a valid tree structure."""
    result = convert_maid_to_efg(prisoners_dilemma_maid)

    root_id = result["root"]
    nodes = result["nodes"]
    outcomes = result["outcomes"]

    # Root should exist in nodes
    assert root_id in nodes, f"Root {root_id} not in nodes"

    # All action targets should reference valid nodes or outcomes
    for node_id, node in nodes.items():
        assert "actions" in node
        for action in node["actions"]:
            target = action.get("target")
            assert target is not None, f"Action in {node_id} has no target"
            assert (
                target in nodes or target in outcomes
            ), f"Target {target} not found in nodes or outcomes"


def test_convert_maid_to_efg_has_outcomes_with_payoffs(prisoners_dilemma_maid):
    """Test that outcomes have proper payoff structure."""
    result = convert_maid_to_efg(prisoners_dilemma_maid)

    outcomes = result["outcomes"]
    players = result["players"]

    assert len(outcomes) > 0, "Should have at least one outcome"

    for outcome_id, outcome in outcomes.items():
        assert "payoffs" in outcome, f"Outcome {outcome_id} missing payoffs"
        payoffs = outcome["payoffs"]

        # Each player should have a payoff
        for player in players:
            assert (
                player in payoffs
            ), f"Player {player} missing from payoffs in {outcome_id}"


def test_convert_maid_to_efg_title(prisoners_dilemma_maid):
    """Test that conversion preserves title."""
    result = convert_maid_to_efg(prisoners_dilemma_maid)
    assert result["title"] == "Prisoner's Dilemma"


def test_convert_maid_to_efg_tags(prisoners_dilemma_maid):
    """Test that conversion adds appropriate tags."""
    result = convert_maid_to_efg(prisoners_dilemma_maid)
    assert "converted" in result["tags"]
    assert "maid-to-efg" in result["tags"]


def test_convert_empty_game_raises_error():
    """Test that converting an invalid game raises an error."""
    with pytest.raises(ValueError) as exc_info:
        convert_maid_to_efg({})

    assert "conversion failed" in str(exc_info.value).lower()


def test_convert_maid_to_efg_includes_node_mapping(prisoners_dilemma_maid):
    """Test that conversion includes MAID-to-EFG node mapping for equilibrium visualization."""
    result = convert_maid_to_efg(prisoners_dilemma_maid)

    # Should have the mapping field
    assert "maid_to_efg_nodes" in result

    mapping = result["maid_to_efg_nodes"]

    # Should have entries for each MAID decision node
    assert "D1" in mapping
    assert "D2" in mapping

    # Each MAID node should map to one or more EFG node IDs
    assert len(mapping["D1"]) >= 1
    assert len(mapping["D2"]) >= 1

    # The mapped EFG node IDs should exist in the nodes dict
    nodes = result["nodes"]
    for maid_node_id, efg_node_ids in mapping.items():
        for efg_node_id in efg_node_ids:
            assert (
                efg_node_id in nodes
            ), f"EFG node {efg_node_id} (mapped from MAID node {maid_node_id}) not in nodes"
