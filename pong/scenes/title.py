from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec
from ..ui.focus import FocusManager, FocusItem
from pong.core.input import Action

logger = logging.getLogger(__name__)


class TitleScene(Scene):
    def __init__(self, manager: SceneManager, screen_rect: pygame.Rect, font_big, font_small, theme) -> None:
        self.manager = manager
        self.font_big = font_big
        self.font_small = font_small
        self.theme = theme
        self._build_buttons(screen_rect)

    def _build_buttons(self, screen_rect: pygame.Rect) -> None:
        w, h = 220, 52
        spacing = 12
        cols = 2
        specs = [
            ButtonSpec("Play", route="play"),
            ButtonSpec("Inventory", route="inventory"),
            ButtonSpec("Shop", route="shop"),
            ButtonSpec("Settings", route="settings"),
            ButtonSpec("Exit", action=self._exit),
        ]
        self.buttons = []
        start_x = screen_rect.centerx - (cols * w + (cols - 1) * spacing) // 2
        start_y = screen_rect.centery - 1 * (h + spacing)
        for idx, spec in enumerate(specs):
            row = idx // cols
            col = idx % cols
            x = start_x + col * (w + spacing)
            y = start_y + row * (h + spacing)
            rect = pygame.Rect(x, y, w, h)
            self.buttons.append(
                button_column(
                    anchor=(x, y),
                    width=w,
                    item_height=h,
                    spacing=0,
                    specs=[spec],
                    font=self.font_small,
                    on_route=self.manager.set_scene,
                    theme=self.theme,
                )[0]
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
        for b in self.buttons:
            b.set_focus(False)
        self.focus.set_items(items)

    def on_event(self, event) -> None:
        from pong.events import ResolutionChanged
        if isinstance(event, ResolutionChanged):
            return

    def on_enter(self, payload=None):
        screen_rect = self.manager.app.screen.get_rect() if hasattr(self.manager, "app") else pygame.Rect(0, 0, 1280, 720)
        self._build_buttons(screen_rect)

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
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        bg = (10, 14, 22) if not palette else _hex_to_rgb(palette.background)
        fg = (255, 200, 120) if not palette else _hex_to_rgb(palette.accent)
        text_fg = (255, 255, 255) if not palette else _hex_to_rgb(palette.foreground)

        screen.fill(bg)
        title = self.font_big.render("BATTLE PONG", True, fg)
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 100))
        subtitle = self.font_small.render("Backbone Preview", True, text_fg)
        screen.blit(subtitle, (screen.get_width() // 2 - subtitle.get_width() // 2, 160))
        for b in self.buttons:
            b.draw(screen)
        logger.debug("Title draw")


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))
