"""Multi-Agent Influence Diagram (MAID) game model.

Represents games as causal DAGs with decision, utility, and chance nodes.
Used for modeling strategic interactions with causal structure.
"""
from __future__ import annotations
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MAIDNode(BaseModel):
    """A node in a MAID (decision, utility, or chance).

    - Decision nodes: controlled by an agent
    - Utility nodes: provide payoffs to an agent
    - Chance nodes: represent probabilistic events
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    type: Literal["chance", "decision", "utility"]
    agent: str | None = None  # Required for decision/utility nodes
    domain: list[Any] = Field(default_factory=list)  # Possible values for this node


class MAIDEdge(BaseModel):
    """A directed edge in the MAID causal graph."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    target: str


class TabularCPD(BaseModel):
    """Tabular Conditional Probability Distribution.

    Specifies the probability distribution over a node's values
    given its parent values. For decision nodes, this represents
    the domain of possible actions.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    node: str
    parents: list[str] = Field(default_factory=list)  # Parent node IDs in order
    values: list[list[float]]  # Probability/payoff table


class MAIDGame(BaseModel):
    """Multi-Agent Influence Diagram game.

    A MAID represents strategic interactions with explicit causal structure.
    Unlike EFG/NFG which model game trees or payoff matrices, MAIDs model
    causal DAGs with decision/utility/chance nodes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    description: str | None = None
    agents: list[str]
    nodes: list[MAIDNode]
    edges: list[MAIDEdge]
    cpds: list[TabularCPD] = Field(default_factory=list)  # Tabular CPD specifications
    tags: list[str] = Field(default_factory=list)
    format_name: Literal["maid"] = "maid"

    @property
    def players(self) -> list[str]:
        """Return agents as players for API compatibility."""
        return self.agents

    @property
    def decisions(self) -> list[MAIDNode]:
        """Return all decision nodes."""
        return [n for n in self.nodes if n.type == "decision"]

    @property
    def utilities(self) -> list[MAIDNode]:
        """Return all utility nodes."""
        return [n for n in self.nodes if n.type == "utility"]

    @property
    def chances(self) -> list[MAIDNode]:
        """Return all chance nodes."""
        return [n for n in self.nodes if n.type == "chance"]

    def get_node(self, node_id: str) -> MAIDNode | None:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_parents(self, node_id: str) -> list[str]:
        """Get parent node IDs for a given node."""
        return [e.source for e in self.edges if e.target == node_id]

    def get_children(self, node_id: str) -> list[str]:
        """Get child node IDs for a given node."""
        return [e.target for e in self.edges if e.source == node_id]
