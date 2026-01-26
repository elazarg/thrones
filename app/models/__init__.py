"""Game models for the workbench."""
from typing import Union

from app.models.extensive_form import Action, DecisionNode, ExtensiveFormGame, Outcome
from app.models.normal_form import NormalFormGame

# Type alias for any game type - used across plugins and converters
AnyGame = Union[ExtensiveFormGame, NormalFormGame]

__all__ = [
    "Action",
    "AnyGame",
    "DecisionNode",
    "ExtensiveFormGame",
    "NormalFormGame",
    "Outcome",
]
