from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Outcome(BaseModel):
    """Terminal node outcome with payoffs per player."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    payoffs: dict[str, float]


class Action(BaseModel):
    """Action available from a decision node."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    probability: float | None = Field(default=None, description="Behavior profile probability")
    target: str | None = Field(default=None, description="ID of the node this action leads to")
    warning: str | None = None


class DecisionNode(BaseModel):
    """Node controlled by a single player."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    player: str
    actions: list[Action]
    information_set: str | None = None
    warning: str | None = None


class ExtensiveFormGame(BaseModel):
    """Minimal representation of an extensive-form game for the MVP."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    description: str | None = None
    players: list[str]
    root: str
    nodes: dict[str, DecisionNode]
    outcomes: dict[str, Outcome]
    tags: list[str] = Field(default_factory=list)
    format_name: Literal["extensive"] = "extensive"
    # Mapping from MAID decision node IDs to EFG node IDs (present when converted from MAID)
    maid_to_efg_nodes: dict[str, list[str]] | None = None

    def reachable_outcomes(self) -> list[Outcome]:
        """Return the list of outcomes reachable from the root.

        Uses depth-first traversal. Order of returned outcomes is not guaranteed
        to match any particular tree ordering (left-to-right, etc.).
        """
        seen: set[str] = set()
        stack = [self.root]  # DFS uses stack (LIFO)
        reachable: list[Outcome] = []

        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)

            node = self.nodes.get(node_id)
            if not node:
                continue

            for action in node.actions:
                if action.target is None:
                    continue

                if action.target in self.outcomes:
                    reachable.append(self.outcomes[action.target])
                else:
                    stack.append(action.target)

        return reachable
