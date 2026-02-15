"""CFR (Counterfactual Regret Minimization) solver for extensive-form games."""

from __future__ import annotations

from typing import Any


def run_cfr_equilibrium(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute approximate Nash equilibrium using CFR.

    CFR iteratively minimizes regret to converge to a Nash equilibrium
    in imperfect-information extensive-form games.

    Args:
        game: Deserialized extensive-form game dict (must include 'efg_content').
        config: Configuration with optional keys:
            - iterations: Number of CFR iterations (default: 1000)
            - algorithm: CFR variant - "cfr", "cfr+", or "mccfr" (default: "cfr+")

    Returns:
        Dict with 'summary' and 'details' containing equilibrium strategy.
    """
    try:
        import pyspiel
    except ImportError as e:
        return {
            "summary": "OpenSpiel not available",
            "details": {"error": f"Failed to import pyspiel: {e}"},
        }

    config = config or {}
    iterations = config.get("iterations", 1000)
    algorithm = config.get("algorithm", "cfr+")

    # Get EFG content from game
    efg_content = game.get("efg_content")
    if not efg_content:
        return {
            "summary": "Error: No EFG content available",
            "details": {"error": "Game must include 'efg_content' for CFR analysis"},
        }

    try:
        # Load game from EFG string
        spiel_game = pyspiel.load_efg_game(efg_content)
    except Exception as e:
        return {
            "summary": f"Error loading game: {str(e)}",
            "details": {"error": f"Failed to parse EFG: {e}"},
        }

    try:
        # Select CFR algorithm
        if algorithm == "cfr":
            from open_spiel.python.algorithms import cfr

            solver = cfr.CFRSolver(spiel_game)
        elif algorithm == "cfr+":
            from open_spiel.python.algorithms import cfr

            solver = cfr.CFRPlusSolver(spiel_game)
        elif algorithm == "mccfr":
            from open_spiel.python.algorithms import external_sampling_mccfr as mccfr

            solver = mccfr.ExternalSamplingSolver(spiel_game, mccfr.AverageType.SIMPLE)
        else:
            return {
                "summary": f"Error: Unknown algorithm '{algorithm}'",
                "details": {"error": f"Unsupported CFR variant: {algorithm}"},
            }

        # Run CFR iterations
        for _ in range(iterations):
            solver.evaluate_and_update_policy()

        # Extract average policy (the converged strategy)
        average_policy = solver.average_policy()

        # Convert policy to serializable format by traversing the game tree
        strategy = {}

        def collect_strategy(state):
            """Recursively collect strategy from all reachable states."""
            if state.is_terminal():
                return
            if state.is_chance_node():
                for action in state.legal_actions():
                    collect_strategy(state.child(action))
                return

            player = state.current_player()
            info_state = state.information_state_string(player)
            legal_actions = state.legal_actions()

            if info_state not in strategy:
                action_probs = average_policy.action_probabilities(state)
                action_names = {}
                for action in legal_actions:
                    prob = action_probs.get(action, 0)
                    action_name = spiel_game.action_to_string(player, action)
                    action_names[action_name] = float(prob)
                strategy[info_state] = action_names

            # Recurse to children
            for action in legal_actions:
                collect_strategy(state.child(action))

        collect_strategy(spiel_game.new_initial_state())

        # Get player names from game data
        player_list = game.get("players", [])

        return {
            "summary": f"CFR equilibrium ({algorithm}, {iterations} iterations)",
            "details": {
                "strategy": strategy,
                "algorithm": algorithm,
                "iterations": iterations,
                "players": player_list,
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }


def run_fictitious_play(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute Nash equilibrium using Fictitious Play.

    Fictitious Play is a classic iterative algorithm where players
    repeatedly best-respond to the empirical distribution of opponent actions.

    Args:
        game: Deserialized extensive-form game dict (must include 'efg_content').
        config: Configuration with optional keys:
            - iterations: Number of FP iterations (default: 1000)

    Returns:
        Dict with 'summary' and 'details' containing equilibrium strategy.
    """
    try:
        import pyspiel
        from open_spiel.python.algorithms import fictitious_play
    except ImportError as e:
        return {
            "summary": "OpenSpiel not available",
            "details": {"error": f"Failed to import modules: {e}"},
        }

    config = config or {}
    iterations = config.get("iterations", 1000)

    efg_content = game.get("efg_content")
    if not efg_content:
        return {
            "summary": "Error: No EFG content available",
            "details": {"error": "Game must include 'efg_content' for Fictitious Play"},
        }

    try:
        spiel_game = pyspiel.load_efg_game(efg_content)

        # Run Fictitious Play
        fp = fictitious_play.XFPSolver(spiel_game)

        for _ in range(iterations):
            fp.iteration()

        # Extract average policy
        average_policy = fp.average_policy()

        # Convert to serializable format
        strategy = {}

        def collect_strategy(state):
            """Recursively collect strategy from all reachable states."""
            if state.is_terminal():
                return
            if state.is_chance_node():
                for action in state.legal_actions():
                    collect_strategy(state.child(action))
                return

            player = state.current_player()
            info_state = state.information_state_string(player)
            legal_actions = state.legal_actions()

            if info_state not in strategy:
                action_probs = average_policy.action_probabilities(state)
                action_names = {}
                for action in legal_actions:
                    prob = action_probs.get(action, 0)
                    action_name = spiel_game.action_to_string(player, action)
                    action_names[action_name] = float(prob)
                strategy[info_state] = action_names

            for action in legal_actions:
                collect_strategy(state.child(action))

        collect_strategy(spiel_game.new_initial_state())

        player_list = game.get("players", [])

        return {
            "summary": f"Fictitious Play equilibrium ({iterations} iterations)",
            "details": {
                "strategy": strategy,
                "algorithm": "fictitious_play",
                "iterations": iterations,
                "players": player_list,
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }


def run_best_response(game: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute best response to a given policy.

    Args:
        game: Deserialized extensive-form game dict.
        config: Configuration with required key:
            - policy: Strategy profile to compute best response against
            - player: Player to compute best response for (default: 0)

    Returns:
        Dict with best response strategy and expected value.
    """
    try:
        import pyspiel
        from open_spiel.python.algorithms import best_response as br
    except ImportError as e:
        return {
            "summary": "OpenSpiel not available",
            "details": {"error": f"Failed to import modules: {e}"},
        }

    config = config or {}
    player = config.get("player", 0)

    efg_content = game.get("efg_content")
    if not efg_content:
        return {
            "summary": "Error: No EFG content available",
            "details": {"error": "Game must include 'efg_content'"},
        }

    try:
        spiel_game = pyspiel.load_efg_game(efg_content)

        # Use uniform random as the opponent policy if none provided
        from open_spiel.python.policy import UniformRandomPolicy

        opponent_policy = UniformRandomPolicy(spiel_game)

        # Compute best response
        best_resp = br.BestResponsePolicy(spiel_game, player, opponent_policy)
        br_value = best_resp.value(spiel_game.new_initial_state())

        return {
            "summary": f"Best response value: {br_value:.4f}",
            "details": {
                "player": player,
                "value": float(br_value),
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }
