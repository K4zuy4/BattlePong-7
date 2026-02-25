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
        self._build_buttons()

    def _resume(self) -> None:
        self.manager.pop()

    def _open_settings(self) -> None:
        self.manager.push("settings")

    def _quit_to_title(self) -> None:
        # clear to title with transition; drop underlying play scene
        self.manager.set_scene("title")

    def _build_buttons(self):
        specs = [
            ButtonSpec("Resume", action=self._resume),
            ButtonSpec("Settings", action=self._open_settings),
            ButtonSpec("Quit to Title", action=self._quit_to_title, variant="ghost"),
        ]
        screen = self.manager.app.screen if hasattr(self.manager, "app") else None
        w, h = 200, 48
        spacing = 12
        if screen:
            rows = len(specs)
            total_h = rows * h + (rows - 1) * spacing
            anchor = (screen.get_width() // 2 - w // 2, screen.get_height() // 2 - total_h // 2)
        else:
            anchor = (60, 180)
        self.buttons = button_column(
            anchor=anchor,
            width=w,
            item_height=h,
            spacing=spacing,
            specs=specs,
            font=self.font_small,
            on_route=self.manager.set_scene,
            theme=self.theme,
        )

    def on_event(self, event) -> None:
        from pong.events import ResolutionChanged
        if isinstance(event, ResolutionChanged):
            return

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
