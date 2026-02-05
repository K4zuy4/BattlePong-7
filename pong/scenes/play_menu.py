from __future__ import annotations

import pygame
import logging

try:
    from .base import Scene, SceneManager
    from ..ui.widgets import Button
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from pong.scenes.base import Scene, SceneManager
    from pong.ui.widgets import Button

logger = logging.getLogger(__name__)


class PlayMenuScene(Scene):
    def __init__(self, manager: SceneManager, app_ctx: dict, font, font_small) -> None:
        self.manager = manager
        self.app_ctx = app_ctx
        self.font = font
        self.font_small = font_small
        self.buttons: list[Button] = []
        w, h = 280, 52
        spacing = 12
        base_y = 180
        opts = [
            ("Einfach", "easy"),
            ("Mittel", "medium"),
            ("Schwer", "hard"),
            ("KI", "ai"),
            ("Zurück", "title"),
        ]
        for i, (label, value) in enumerate(opts):
            rect = pygame.Rect(160, base_y + i * (h + spacing), w, h)
            self.buttons.append(Button(rect, label, font_small, lambda v=value: self._select(v)))

    def _select(self, value) -> None:
        if value is None:
            return
        if value == "title":
            self.manager.set_scene("mode_select")
            return
        self.app_ctx["bot_difficulty"] = value
        self.manager.set_scene("play")
        logger.info("Bot difficulty selected", extra={"mode": value})

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((20, 24, 36))
        title = self.font.render("Singleplayer Bots", True, (220, 220, 240))
        screen.blit(title, (80, 100))
        for b in self.buttons:
            b.draw(screen)
