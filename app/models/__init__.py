"""Game models for the workbench."""

from typing import Union

from app.models.extensive_form import Action, DecisionNode, ExtensiveFormGame, Outcome
from app.models.normal_form import NormalFormGame
from app.models.maid import MAIDEdge, MAIDGame, MAIDNode, TabularCPD
from app.models.vegas import VegasGame
from app.models.efg_string import EfgStringGame

# Type alias for any game type - used across plugins and converters
AnyGame = Union[ExtensiveFormGame, NormalFormGame, MAIDGame, VegasGame, EfgStringGame]

__all__ = [
    "Action",
    "AnyGame",
    "DecisionNode",
    "EfgStringGame",
    "ExtensiveFormGame",
    "MAIDEdge",
    "MAIDGame",
    "MAIDNode",
    "NormalFormGame",
    "Outcome",
    "TabularCPD",
    "VegasGame",
]
