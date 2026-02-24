from __future__ import annotations

"""Lightweight transition controller placeholder.

For now transitions are instantaneous; the controller keeps the API surface so
we can plug fade/slide without rewriting scenes.
"""

from dataclasses import dataclass
from typing import Callable, Optional
import pygame

from ..ui.tween import tween


@dataclass
class TransitionSpec:
    name: str = "instant"  # "instant", "fade", "slide_left"
    duration: float = 0.0
    easing: str = "linear"
    color: tuple[int, int, int] = (0, 0, 0)


class TransitionController:
    """Simple one-shot transition controller (cover overlay).

    Current behavior: overlays the current frame; switches scene when complete.
    Fade uses alpha; slide draws a covering rect from the left.
    """

    def __init__(self) -> None:
        self.active = False
        self.spec = TransitionSpec()
        self._time = 0.0
        self._on_complete: Optional[Callable[[], None]] = None

    def start(self, spec: TransitionSpec, on_complete: Callable[[], None]) -> None:
        self.spec = spec
        self._time = 0.0
        self._on_complete = on_complete
        self.active = spec.duration > 0
        if not self.active:
            on_complete()

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self._time += dt
        if self._time >= self.spec.duration:
            self.active = False
            if self._on_complete:
                self._on_complete()

    def progress(self) -> float:
        if not self.active or self.spec.duration <= 0:
            return 0.0
        return min(1.0, self._time / self.spec.duration)

    def draw_overlay(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        p = tween(self.progress(), self.spec.easing)
        if self.spec.name == "fade":
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            alpha = int(255 * p)
            overlay.fill((*self.spec.color, alpha))
            screen.blit(overlay, (0, 0))
        elif self.spec.name == "slide_left":
            width = int(screen.get_width() * p)
            rect = pygame.Rect(0, 0, width, screen.get_height())
            overlay = pygame.Surface((width, screen.get_height()))
            overlay.fill(self.spec.color)
            screen.blit(overlay, rect)
        # instant or unknown: no overlay
