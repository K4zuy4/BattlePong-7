from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec
from ..ui.focus import FocusManager, FocusItem
from pong.core.input import Action

logger = logging.getLogger(__name__)


class TitleScene(Scene):
    def __init__(self, manager: SceneManager, screen_rect: pygame.Rect, font_big, font_small) -> None:
        self.manager = manager
        self.font_big = font_big
        self.font_small = font_small
        w, h = 260, 56
        spacing = 18
        start_y = screen_rect.centery - 2 * (h + spacing) / 2
        specs = [
            ButtonSpec("Play", route="play"),
            ButtonSpec("Settings", route="settings"),
            ButtonSpec("Exit", action=self._exit),
        ]
        anchor = (screen_rect.centerx - w // 2, int(start_y))
        self.buttons = button_column(
            anchor=anchor,
            width=w,
            item_height=h,
            spacing=spacing,
            specs=specs,
            font=font_small,
            on_route=self.manager.set_scene,
        )
        self.focus = FocusManager()
        items = [
            FocusItem(
                rect=b.rect,
                on_focus=lambda btn=b: btn.set_focus(True),
                on_activate=lambda btn=b: btn.on_click(),
            )
            for b in self.buttons
        ]
        # clear focus setter resets others
        for b in self.buttons:
            b.set_focus(False)
        self.focus.set_items(items)

    def _exit(self) -> None:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        logger.info("Exit requested from Title")

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def handle_input(self, input_state) -> None:
        delta = input_state.nav_vertical()
        if delta != 0:
            # clear all focus flags
            for b in self.buttons:
                b.set_focus(False)
            self.focus.move(delta)
        if hasattr(input_state, "consume") and input_state.consume(Action.CONFIRM):
            self.focus.activate()

    def update(self, dt: float) -> None:
        for b in self.buttons:
            b.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((10, 14, 22))
        title = self.font_big.render("BATTLE PONG", True, (255, 200, 120))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 100))
        subtitle = self.font_small.render("Backbone Preview", True, (180, 200, 220))
        screen.blit(subtitle, (screen.get_width() // 2 - subtitle.get_width() // 2, 160))
        for b in self.buttons:
            b.draw(screen)
        logger.debug("Title draw")
