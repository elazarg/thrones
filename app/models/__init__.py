"""Game models for the workbench."""

from typing import Union

from app.models.extensive_form import Action, DecisionNode, ExtensiveFormGame, Outcome
from app.models.normal_form import NormalFormGame
from app.models.maid import MAIDEdge, MAIDGame, MAIDNode, TabularCPD
from app.models.vegas import VegasGame

# Type alias for any game type - used across plugins and converters
AnyGame = Union[ExtensiveFormGame, NormalFormGame, MAIDGame, VegasGame]

__all__ = [
    "Action",
    "AnyGame",
    "DecisionNode",
    "ExtensiveFormGame",
    "MAIDEdge",
    "MAIDGame",
    "MAIDNode",
    "NormalFormGame",
    "Outcome",
    "TabularCPD",
    "VegasGame",
]
