from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from .versioning import VersionStatus


ChangeKind = Literal["add", "modify", "not_applicable"]


@dataclass(frozen=True)
class ProjectFacts:
    profile_id: str
    profile_name: str
    confidence: int
    project_root: Path
    build_system: str
    java_version: str
    dockerfile: str | None
    evidence: tuple[str, ...] = ()

    def public(self) -> dict:
        data = asdict(self)
        data["project_root"] = "."
        data["evidence"] = list(self.evidence)
        return data


@dataclass(frozen=True)
class Change:
    kind: ChangeKind
    path: str
    title: str
    reason: str
    line: int | None = None
    before: str | None = None
    after: str | None = None


@dataclass(frozen=True)
class LearningCard:
    title: str
    summary: str
    checks: tuple[str, ...] = ()


@dataclass
class AnalysisPlan:
    facts: ProjectFacts
    changes: list[Change] = field(default_factory=list)
    learning: list[LearningCard] = field(default_factory=list)
    version: VersionStatus | None = None

    def public(self) -> dict:
        result = {
            "facts": self.facts.public(),
            "changes": [asdict(item) for item in self.changes],
            "learning": [asdict(item) for item in self.learning],
        }
        if self.version:
            result["version"] = self.version.public()
        return result
