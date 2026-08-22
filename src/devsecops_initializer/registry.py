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
        """Devuelve el perfil que reconoce el proyecto con mayor confianza."""
        confidence, profile = max(
            ((profile.detect(root), profile) for profile in self._profiles),
            key=lambda item: item[0],
        )
        if confidence < 60:
            raise ProfileNotDetected("No se ha detectado un framework compatible.")
        return profile, confidence
