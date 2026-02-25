from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec
from ..ui.widgets import Label
from ..ui.focus import FocusManager, FocusItem
from pong.core.input import Action

logger = logging.getLogger(__name__)


class SkinsScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small, theme) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.theme = theme
        self.focus = FocusManager()
        self.buttons = []
        self.status_msg = ""
        self._rebuild_buttons()

    def _rebuild_buttons(self) -> None:
        specs = [
            ButtonSpec("Apply", action=self._apply_selected),
            ButtonSpec("Buy", action=self._buy_selected, variant="primary"),
            ButtonSpec("Back", action=self._back, variant="ghost"),
        ]
        self.buttons = button_column(
            anchor=(40, 360),
            width=200,
            item_height=44,
            spacing=10,
            specs=specs,
            font=self.font_small,
            on_route=self.manager.set_scene,
            theme=self.theme,
        )
        items = [
            FocusItem(rect=b.rect, on_focus=lambda btn=b: btn.set_focus(True), on_activate=lambda btn=b: btn.on_click())
            for b in self.buttons
        ]
        for b in self.buttons:
            b.set_focus(False)
        self.focus.set_items(items)

    def on_enter(self, payload: dict | None = None) -> None:
        # select first skin by default
        self._skin_list = self.manager.app_ctx.get("skin_names", []) if hasattr(self.manager, "app_ctx") else []
        self._owned = self.manager.app_ctx.get("owned_skins", set()) if hasattr(self.manager, "app_ctx") else set()
        self._selected_idx = 0
        self.status_msg = ""
        logger.info("SkinsScene enter", extra={"skins": self._skin_list})

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def handle_input(self, input_state) -> None:
        delta = input_state.nav_vertical()
        if delta != 0:
            for b in self.buttons:
                b.set_focus(False)
            self.focus.move(delta)
        if hasattr(input_state, "consume") and input_state.consume(Action.CONFIRM):
            self.focus.activate()
        # cycle skins with horizontal nav
        h = input_state.nav_horizontal() if hasattr(input_state, "nav_horizontal") else 0
        if h != 0 and self._skin_list:
            self._selected_idx = (self._selected_idx + h) % len(self._skin_list)

    def update(self, dt: float) -> None:
        for b in self.buttons:
            b.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        bg = (12, 16, 22) if not palette else _hex_to_rgb(palette.background)
        screen.fill(bg)
        title = self.font.render("Skins", True, (240, 240, 255))
        screen.blit(title, (40, 40))

        credits = self.manager.app_ctx.get("credits", 0)
        credits_txt = self.font_small.render(f"Credits: {credits}", True, (220, 230, 240))
        screen.blit(credits_txt, (40, 70))

        skin_name = self._skin_list[self._selected_idx] if self._skin_list else "none"
        owned = skin_name in self._owned
        info = f"Selected: {skin_name} ({'Owned' if owned else 'Not owned'})"
        info_txt = self.font_small.render(info, True, (220, 230, 240))
        screen.blit(info_txt, (40, 100))

        # Palette preview
        if palette:
            swatches = [palette.background, palette.primary, palette.accent, palette.foreground, palette.highlight]
        else:
            swatches = ["#0e111a", "#5b8cff", "#ffb86c", "#e6e6e6", "#ffffff"]
        for i, col in enumerate(swatches):
            c = _hex_to_rgb(col)
            pygame.draw.rect(screen, c, pygame.Rect(40 + i * 64, 160, 60, 60), border_radius=8)

        if self.status_msg:
            msg = self.font_small.render(self.status_msg, True, (255, 210, 180))
            screen.blit(msg, (40, 240))

        for b in self.buttons:
            b.draw(screen)

    def _apply_selected(self) -> None:
        if not self._skin_list:
            return
        name = self._skin_list[self._selected_idx]
        owned_items = self.manager.app_ctx.get("owned_items", {}) if hasattr(self.manager, "app_ctx") else {}
        owned = owned_items.get("ball", set()) if isinstance(owned_items, dict) else set()
        if name not in owned:
            logger.info("Apply blocked, not owned", extra={"skin": name})
            self.status_msg = "Not owned"
            return
        app = getattr(self.manager, "app", None)
        if app and hasattr(app, "_apply_skin"):
            app._apply_skin(name)
            self.status_msg = f"Applied {name}"
            logger.info("Skin applied via scene", extra={"skin": name})

    def _buy_selected(self) -> None:
        if not self._skin_list:
            return
        name = self._skin_list[self._selected_idx]
        app = getattr(self.manager, "app", None)
        if not app:
            return
        if name in app.owned_items.get("ball", set()):
            self.status_msg = "Already owned"
            logger.info("Purchase skipped; already owned", extra={"skin": name})
            return
        price = 1000 if name.lower().startswith("basic") else 2000
        if app.credits < price:
            need = price - app.credits
            self.status_msg = f"Need {need} more credits"
            logger.info("Not enough credits", extra={"need": price, "have": app.credits})
            return
        before = app.credits
        app.credits -= price
        app.owned_items.setdefault("ball", set()).add(name)
        app._save_wallet()
        app._save_owned_items()
        self.manager.app_ctx["owned_items"] = app.owned_items
        self.manager.app_ctx["credits"] = app.credits
        self.status_msg = f"Bought {name} for {price}C"
        logger.info(
            "Skin purchased",
            extra={"skin": name, "price": price, "credits_before": before, "credits_after": app.credits},
        )

    def _back(self) -> None:
        # If opened via set_scene (stack size 1), go back to title; otherwise pop overlay
        if self.manager.previous_name:
            self.manager.pop()
        else:
            self.manager.set_scene("title")


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))
