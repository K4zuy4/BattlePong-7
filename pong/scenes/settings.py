from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec
from ..ui.widgets import Button
from pong.core.input import Action, default_action_keys

logger = logging.getLogger(__name__)

class SettingsScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small, theme=None) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.theme = theme
        self.buttons = []
        self.binding_buttons: list[Button] = []
        self.listening_for: str | None = None
        self.status = ""
        self.res_index = 0
        self._rebuild()

    # lifecycle --------------------------------------------------------- #
    def on_enter(self, payload=None):
        self._rebuild()
        self.status = ""
        self.listening_for = None

    def _rebuild(self):
        self._load_state()
        self._build_binding_buttons()
        self._build_misc_buttons()

    def _load_state(self):
        app = getattr(self.manager, "app", None)
        if not app:
            self.action_keys = default_action_keys()
            self.res_index = 0
            self.debug_overlay_enabled = False
            return
        cfg = app.input_cfg if isinstance(app.input_cfg, dict) else {}
        keys = default_action_keys()
        for k, v in cfg.items():
            try:
                keys[k] = int(v)
            except Exception:
                pass
        self.action_keys = keys
        self.res_index = 0
        self.debug_overlay_enabled = app.debug_overlay_visible()

    def _build_binding_buttons(self):
        self.binding_buttons = []
        anchor_x, anchor_y = 60, 140
        w, h = 220, 44
        spacing = 12
        actions = ["UP", "DOWN", "CONFIRM", "BACK", "PAUSE"]
        for i, act in enumerate(actions):
            keycode = self.action_keys.get(act, -1)
            keyname = "-" if keycode is None or keycode < 0 else pygame.key.name(keycode)
            label = f"{act}: {keyname}"
            rect = pygame.Rect(anchor_x, anchor_y + i * (h + spacing), w, h)
            self.binding_buttons.append(Button(rect, label, self.font_small, on_click=lambda a=act: self._start_listen(a), variant="primary", theme=self.theme))

    def _build_misc_buttons(self):
        w, h = 200, 48
        spacing = 12
        anchor = (60, 420)
        specs = [
            ButtonSpec(
                f"Debug Overlay: {'On' if self.debug_overlay_enabled else 'Off'}",
                action=self._toggle_debug_overlay,
            ),
            ButtonSpec("Back", action=self._back, variant="ghost"),
        ]
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

    # interactions ------------------------------------------------------ #
    def _start_listen(self, action_name: str):
        self.listening_for = action_name
        self.status = f"Press new key for {action_name}"
        logger.info("Rebind start", extra={"action": action_name})

    def _back(self) -> None:
        in_game = False
        if hasattr(self.manager, "app_ctx") and isinstance(self.manager.app_ctx, dict):
            in_game = self.manager.app_ctx.get("in_game", False)

        if in_game:
            self.manager.pop()
        else:
            if self.manager.previous_name == "title":
                self.manager.pop()
            else:
                self.manager.set_scene("title")
        logger.info("Settings back", extra={"in_game": in_game})

    def _toggle_debug_overlay(self) -> None:
        app = getattr(self.manager, "app", None)
        if not app:
            return
        app.set_debug_overlay_visible(not app.debug_overlay_visible())
        self.debug_overlay_enabled = app.debug_overlay_visible()
        self.status = f"Debug overlay {'enabled' if self.debug_overlay_enabled else 'disabled'}"
        self._build_misc_buttons()

    # event/input ------------------------------------------------------- #
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.listening_for and event.type == pygame.KEYDOWN:
            self._finish_rebind(event.key)
            return
        for b in self.binding_buttons:
            b.handle_event(event)
        for b in self.buttons:
            b.handle_event(event)

    def _finish_rebind(self, key: int):
        action = self.listening_for
        self.listening_for = None
        if not action:
            return
        # remove key from other actions
        for k, v in list(self.action_keys.items()):
            if v == key and k != action:
                self.action_keys[k] = None
        self.action_keys[action] = key
        # rebuild keymap & save
        app = getattr(self.manager, "app", None)
        if app:
            cleaned = {k: v for k, v in self.action_keys.items() if v is not None}
            app.save_input_cfg(cleaned)
            app.input.keymap = app._build_keymap()
        self._build_binding_buttons()
        self.status = f"{action} -> {pygame.key.name(key)}"
        logger.info("Rebind applied", extra={"action": action, "key": key})

    def handle_input(self, input_state) -> None:
        if input_state.consume(Action.BACK):
            self._back()

    def update(self, dt: float) -> None:
        for b in self.binding_buttons:
            b.update(dt)
        for b in self.buttons:
            b.update(dt)

    # drawing ----------------------------------------------------------- #
    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((16, 20, 28))
        title = self.font.render("Settings", True, (230, 230, 230))
        screen.blit(title, (40, 40))
        subtitle = self.font_small.render("Keybinds", True, (200, 210, 220))
        screen.blit(subtitle, (40, 100))

        for b in self.binding_buttons:
            b.draw(screen)

        for b in self.buttons:
            b.draw(screen)

        if self.status:
            msg = self.font_small.render(self.status, True, (210, 220, 255))
            screen.blit(msg, (40, 360))
