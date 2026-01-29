"""Tests for Vegas parser and compiler."""

import pytest

from vegas_plugin.parser import parse_vg, compile_to_maid, compile_to_target, COMPILE_TARGETS


PRISONERS_VG = '''
game main() {
  join A() $ 100;
  join B() $ 100;
  yield or split A(c: bool) B(c: bool);
  withdraw
    (A.c && B.c )   ? { A -> 100; B -> 100 }
  : (A.c && !B.c) ? { A -> 0; B -> 200 }
  : (!A.c && B.c) ? { A -> 200; B -> 0 }
  :                 { A -> 90; B -> 110 }
}
'''


def test_parse_vg_returns_vegas_game():
    """Test parsing a .vg file returns a VegasGame dict."""
    game = parse_vg(PRISONERS_VG, "prisoners.vg")

    assert game["format_name"] == "vegas"
    assert "source_code" in game
    assert "game main()" in game["source_code"]
    assert set(game["players"]) == {"A", "B"}
    assert game["title"] == "prisoners"  # from filename


def test_parse_vg_extracts_players():
    """Test that players are extracted from join statements."""
    game = parse_vg(PRISONERS_VG, "test.vg")
    assert "A" in game["players"]
    assert "B" in game["players"]


def test_compile_to_maid_returns_maid_game():
    """Test compiling .vg to MAID produces valid MAID structure."""
    game = compile_to_maid(PRISONERS_VG, "prisoners.vg")

    assert game["format_name"] == "maid"
    assert set(game["agents"]) == {"A", "B"}

    # Should have 2 decision nodes + 2 utility nodes
    decision_nodes = [n for n in game["nodes"] if n["type"] == "decision"]
    utility_nodes = [n for n in game["nodes"] if n["type"] == "utility"]

    assert len(decision_nodes) == 2
    assert len(utility_nodes) == 2

    # Should have edges from decisions to utilities
    assert len(game["edges"]) == 4

    # Should have CPDs for utility nodes
    assert len(game["cpds"]) == 2


def test_compile_invalid_vg_raises_error():
    """Test that invalid .vg content raises an error on compile."""
    with pytest.raises(ValueError) as exc_info:
        compile_to_maid("invalid syntax {{{", "bad.vg")

    assert "failed" in str(exc_info.value).lower()


def test_parse_simple_game():
    """Test parsing a simple game."""
    simple_vg = '''
    game main() {
      join A() $ 10;
      join B() $ 10;
      yield or split A(x: bool) B(y: bool);
      withdraw { A -> 10; B -> 10 }
    }
    '''
    game = parse_vg(simple_vg, "simple.vg")

    assert game["format_name"] == "vegas"
    assert "A" in game["players"]
    assert "B" in game["players"]
    assert "source_code" in game


# ---------------------------------------------------------------------------
# compile_to_target tests
# ---------------------------------------------------------------------------


def test_compile_to_solidity():
    """Test compiling .vg to Solidity."""
    result = compile_to_target(PRISONERS_VG, "solidity", "prisoners.vg")

    assert result["type"] == "code"
    assert result["language"] == "solidity"
    assert "pragma solidity" in result["content"] or "contract" in result["content"]


def test_compile_to_vyper():
    """Test compiling .vg to Vyper."""
    result = compile_to_target(PRISONERS_VG, "vyper", "prisoners.vg")

    assert result["type"] == "code"
    assert result["language"] == "vyper"
    # Vyper uses @external or @internal decorators
    assert "@" in result["content"] or "#" in result["content"]


def test_compile_to_smt():
    """Test compiling .vg to SMT-LIB."""
    result = compile_to_target(PRISONERS_VG, "smt", "prisoners.vg")

    assert result["type"] == "code"
    assert result["language"] == "smt-lib"
    # SMT-LIB uses s-expressions
    assert "(" in result["content"]


def test_compile_to_scribble():
    """Test compiling .vg to Scribble protocol."""
    result = compile_to_target(PRISONERS_VG, "scribble", "prisoners.vg")

    assert result["type"] == "code"
    assert result["language"] == "scribble"
    # Scribble defines protocols
    assert "protocol" in result["content"].lower() or "role" in result["content"].lower()


def test_compile_to_unknown_target_raises():
    """Test that compiling to unknown target raises an error."""
    with pytest.raises(ValueError) as exc_info:
        compile_to_target(PRISONERS_VG, "unknown_target", "test.vg")

    assert "Unknown compile target" in str(exc_info.value)


def test_compile_targets_dict_has_all_fields():
    """Test that COMPILE_TARGETS has all required fields."""
    required_fields = {"id", "type", "language", "label", "flag", "extension"}

    for target_id, target_info in COMPILE_TARGETS.items():
        for field in required_fields:
            assert field in target_info, f"Missing {field} in {target_id}"
