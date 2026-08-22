from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Change, LearningCard, ProjectFacts


class FrameworkProfile(ABC):
    id: str
    name: str

    @abstractmethod
    def detect(self, root: Path) -> int:
        """Devuelve un nivel de confianza entre 0 y 100."""

    @abstractmethod
    def inspect(self, root: Path, confidence: int) -> ProjectFacts:
        """Extrae información normalizada del proyecto."""

    @abstractmethod
    def plan(self, facts: ProjectFacts) -> list[Change]:
        """Describe los cambios del perfil sin aplicarlos."""

    @abstractmethod
    def learning_content(self, facts: ProjectFacts) -> list[LearningCard]:
        """Devuelve las orientaciones necesarias para comprender los controles."""
