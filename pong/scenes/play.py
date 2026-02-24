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
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        bg = (12, 16, 26) if not palette else _hex_to_rgb(palette.background)
        screen.fill(bg)

    def _draw_world(self, screen: pygame.Surface) -> None:
        # Placeholder: oscillating circle to show world layer separation
        import math

        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        color = (90, 140, 255) if not palette else _hex_to_rgb(palette.accent)
        cx = screen.get_width() // 2
        cy = screen.get_height() // 2
        r = 40 + int(10 * math.sin(self.time * 2))
        pygame.draw.circle(screen, color, (cx, cy), r)

    def _draw_ui(self, screen: pygame.Surface) -> None:
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        fg = (240, 220, 180) if not palette else _hex_to_rgb(palette.foreground)
        title = self.font.render("Play Stub", True, fg)
        screen.blit(title, (40, 40))
        hint = self.font_small.render("[Esc/P] Pause", True, fg)
        screen.blit(hint, (40, 90))


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))
