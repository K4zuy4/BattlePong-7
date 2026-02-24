from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec

logger = logging.getLogger(__name__)


class PauseScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small, theme) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.theme = theme
        specs = [
            ButtonSpec("Resume", action=self._resume),
            ButtonSpec("Settings", action=self._open_settings),
            ButtonSpec("Quit to Title", action=self._quit_to_title, variant="ghost"),
        ]
        self.buttons = button_column(
            anchor=(60, 180),
            width=200,
            item_height=48,
            spacing=12,
            specs=specs,
            font=font_small,
            on_route=self.manager.set_scene,
            theme=theme,
        )

    def _resume(self) -> None:
        self.manager.pop()

    def _open_settings(self) -> None:
        self.manager.push("settings")

    def _quit_to_title(self) -> None:
        # clear to title with transition; drop underlying play scene
        self.manager.set_scene("title")

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        for b in self.buttons:
            b.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        title = self.font.render("Paused", True, (255, 255, 255))
        screen.blit(title, (60, 120))
        for b in self.buttons:
            b.draw(screen)
