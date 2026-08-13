from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Change, LearningCard, ProjectFacts


class FrameworkProfile(ABC):
    id: str
    name: str

    @abstractmethod
    def detect(self, root: Path) -> int:
        """Return a confidence score between 0 and 100."""

    @abstractmethod
    def inspect(self, root: Path, confidence: int) -> ProjectFacts:
        """Extract normalized facts from the project."""

    @abstractmethod
    def plan(self, facts: ProjectFacts) -> list[Change]:
        """Describe framework-specific changes without applying them."""

    @abstractmethod
    def learning_content(self, facts: ProjectFacts) -> list[LearningCard]:
        """Return concise educational guidance for this profile."""

