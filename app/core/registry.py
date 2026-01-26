"""Lightweight plugin registry for the MVP.

This keeps the initial surface area small while matching the design goal
of a plugin-driven system. Plugins register themselves by calling
``registry.register_plugin`` at import time.
"""
from __future__ import annotations

from typing import Any, Protocol, Iterable, runtime_checkable

from pydantic import BaseModel, ConfigDict

from app.models.extensive_form import ExtensiveFormGame


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    summary: str
    details: dict[str, Any]


@runtime_checkable
class AnalysisPlugin(Protocol):
    """Interface for analysis plugins.

    The MVP only uses a subset of the interface from the design doc,
    focusing on metadata and a single synchronous ``run`` method.
    """

    name: str
    description: str
    applicable_to: tuple[str, ...]
    continuous: bool

    def can_run(self, game: ExtensiveFormGame) -> bool:
        ...

    def run(self, game: ExtensiveFormGame, config: dict | None = None) -> AnalysisResult:
        ...

    def summarize(self, result: AnalysisResult) -> str:
        ...


class Registry:
    def __init__(self) -> None:
        self._analysis: dict[str, AnalysisPlugin] = {}

    def register_analysis(self, plugin: AnalysisPlugin) -> None:
        self._analysis[plugin.name] = plugin

    def analyses(self) -> Iterable[AnalysisPlugin]:
        return self._analysis.values()

    def get_analysis(self, name: str) -> AnalysisPlugin | None:
        return self._analysis.get(name)


registry = Registry()
"""Global registry instance used by the FastAPI app."""
