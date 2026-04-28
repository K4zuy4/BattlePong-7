from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec
from pong.core.input import Action

logger = logging.getLogger(__name__)


class ShopScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small, theme) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.theme = theme
        self.status_msg = ""
        self.packages = [
            {"label": "Buy 1000C for 9.999€", "credits": 1000},
            {"label": "Buy 5000C for 49.999€", "credits": 5000},
        ]
        specs = [
            ButtonSpec("1000C Pack", action=lambda: self._buy_pack(0)),
            ButtonSpec("5000C Pack", action=lambda: self._buy_pack(1)),
            ButtonSpec("Back", action=self._back, variant="ghost"),
        ]
        self.buttons = button_column(
            anchor=(40, 220),
            width=260,
            item_height=48,
            spacing=12,
            specs=specs,
            font=font_small,
            on_route=self.manager.set_scene,
            theme=theme,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def handle_input(self, input_state) -> None:
        delta = input_state.nav_vertical()
        if delta:
            for b in self.buttons:
                b.set_focus(False)
        if delta == -1:
            self.buttons[0].set_focus(True)
        elif delta == 1:
            self.buttons[1].set_focus(True)
        if hasattr(input_state, "consume") and input_state.consume(Action.CONFIRM):
            # activate focused if any
            for b in self.buttons:
                if getattr(b, "focused", False):
                    b.on_click()
                    break

    def update(self, dt: float) -> None:
        for b in self.buttons:
            b.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        bg = (14, 14, 24) if not palette else _hex_to_rgb(palette.background)
        fg = (240, 200, 120) if not palette else _hex_to_rgb(palette.foreground)
        screen.fill(bg)
        title = self.font.render("Satire Shop", True, fg)
        screen.blit(title, (40, 40))
        credits = self.manager.app_ctx.get("credits", 0)
        credits_txt = self.font_small.render(f"Credits: {credits}", True, fg)
        screen.blit(credits_txt, (40, 100))
        subtitle = self.font_small.render("Kaufe mehr Credits", True, fg)
        screen.blit(subtitle, (40, 140))
        if self.status_msg:
            msg = self.font_small.render(self.status_msg, True, (255, 210, 180))
            screen.blit(msg, (40, 180))
        for b in self.buttons:
            b.draw(screen)

    def _buy_pack(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.packages):
            return
        pack = self.packages[idx]
        app = getattr(self.manager, "app", None)
        if not app:
            return
        app.credits += pack["credits"]
        app._save_wallet()
        self.manager.app_ctx["credits"] = app.credits
        self.status_msg = f"Granted {pack['credits']}C"
        logger.info("Credits granted", extra={"credits": app.credits, "pack": pack})

    def _back(self) -> None:
        if self.manager.previous_name:
            self.manager.pop()
        else:
            self.manager.set_scene("title")


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))
