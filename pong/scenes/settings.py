from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec

logger = logging.getLogger(__name__)


class SettingsScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        w, h = 200, 48
        spacing = 12
        anchor = (80, 200)
        specs = [
            ButtonSpec("Back", action=self._back, variant="ghost"),
        ]
        self.buttons = button_column(
            anchor=anchor,
            width=w,
            item_height=h,
            spacing=spacing,
            specs=specs,
            font=font_small,
            on_route=self.manager.set_scene,
        )

    def _back(self) -> None:
        # if in-game (settings opened from pause/play), go back to pause; else go to title
        in_game = False
        if hasattr(self.manager, "app_ctx") and isinstance(self.manager.app_ctx, dict):
            in_game = self.manager.app_ctx.get("in_game", False)

        if in_game:
            # Settings wurde via push geöffnet -> pop zurück zum vorherigen (Pause)
            self.manager.pop()
        else:
            if self.manager.previous_name == "title":
                self.manager.pop()
            else:
                self.manager.set_scene("title")
        logger.info("Settings back", extra={"in_game": in_game})

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        for b in self.buttons:
            b.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((16, 20, 28))
        title = self.font.render("Settings", True, (230, 230, 230))
        screen.blit(title, (40, 40))
        desc = self.font_small.render("Placeholder for runtime settings UI", True, (180, 200, 200))
        screen.blit(desc, (40, 90))
        for b in self.buttons:
            b.draw(screen)
        logger.debug("Settings draw")
