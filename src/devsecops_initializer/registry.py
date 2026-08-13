from __future__ import annotations

from pathlib import Path

from .profiles.base import FrameworkProfile
from .profiles.spring_boot import SpringBootProfile


class ProfileNotDetected(ValueError):
    pass


class ProfileRegistry:
    def __init__(self, profiles: list[FrameworkProfile] | None = None):
        self._profiles = profiles or [SpringBootProfile()]

    def resolve(self, root: Path) -> tuple[FrameworkProfile, int]:
        ranked = sorted(((profile.detect(root), profile) for profile in self._profiles), reverse=True, key=lambda item: item[0])
        confidence, profile = ranked[0]
        if confidence < 60:
            raise ProfileNotDetected("No se ha detectado un framework compatible con suficiente confianza.")
        return profile, confidence

