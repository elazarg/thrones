"""Tests for Vegas parser."""

import pytest

from vegas_plugin.parser import parse_vg


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


def test_parse_prisoners_dilemma():
    """Test parsing Prisoner's Dilemma .vg file."""
    game = parse_vg(PRISONERS_VG, "prisoners.vg")

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


def test_parse_invalid_vg_raises_error():
    """Test that invalid .vg content raises an error."""
    with pytest.raises(ValueError) as exc_info:
        parse_vg("invalid syntax {{{", "bad.vg")

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

    assert game["format_name"] == "maid"
    assert "A" in game["agents"]
    assert "B" in game["agents"]
