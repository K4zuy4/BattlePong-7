from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager

logger = logging.getLogger(__name__)


class PlayScene(Scene):
    """Stub play scene with clear layer hooks (bg/world/ui)."""

    def __init__(self, manager: SceneManager, font, font_small) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.time = 0.0

    # Event handling ----------------------------------------------------- #
    def handle_event(self, event: pygame.event.Event) -> None:
        # ESC/P handled globally in app loop
        return

    # Simulation --------------------------------------------------------- #
    def update(self, dt: float) -> None:
        self.time += dt

    # Rendering layers --------------------------------------------------- #
    def draw(self, screen: pygame.Surface) -> None:
        self._draw_background(screen)
        self._draw_world(screen)
        self._draw_ui(screen)

    def _draw_background(self, screen: pygame.Surface) -> None:
        screen.fill((12, 16, 26))

    def _draw_world(self, screen: pygame.Surface) -> None:
        # Placeholder: oscillating circle to show world layer separation
        import math

        cx = screen.get_width() // 2
        cy = screen.get_height() // 2
        r = 40 + int(10 * math.sin(self.time * 2))
        pygame.draw.circle(screen, (90, 140, 255), (cx, cy), r)

    def _draw_ui(self, screen: pygame.Surface) -> None:
        title = self.font.render("Play Stub", True, (240, 220, 180))
        screen.blit(title, (40, 40))
        hint = self.font_small.render("[Esc/P] Pause", True, (200, 210, 220))
        screen.blit(hint, (40, 90))
