from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.registry import AnalysisResult, registry
from app.models.game import Action, DecisionNode, Game, Outcome

# Import plugins for registration side effects
from app.plugins import discover_plugins

discover_plugins()

app = FastAPI(title="Game Theory Workbench MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


TRUST_GAME = Game(
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
                Action(label="Betray", target="o_betray", warning="Dominated by Honor"),
            ],
        ),
    },
    outcomes={
        "o_coop": Outcome(label="Cooperate", payoffs={"Alice": 1, "Bob": 1}),
        "o_betray": Outcome(label="Betray", payoffs={"Alice": -1, "Bob": 2}),
        "o_decline": Outcome(label="Decline", payoffs={"Alice": 0, "Bob": 0}),
    },
    version="v3",
    tags=["sequential", "2-player", "symmetric"],
)


@app.get("/api/game", response_model=Game)
def get_game() -> Game:
    return TRUST_GAME


@app.get("/api/analyses", response_model=list[AnalysisResult])
def run_continuous_analyses() -> list[AnalysisResult]:
    return [
        plugin.run(TRUST_GAME)
        for plugin in registry.analyses()
        if plugin.continuous and plugin.can_run(TRUST_GAME)
    ]


# Serve a minimal static prototype for the canvas and status bar
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
