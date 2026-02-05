from __future__ import annotations

import pygame
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    __package__ = "pong.scenes"

from .base import Scene, SceneManager
from ..ui.widgets import Button

logger = logging.getLogger(__name__)


class TitleScene(Scene):
    def __init__(self, manager: SceneManager, screen_rect: pygame.Rect, font_big, font_small) -> None:
        self.manager = manager
        self.font_big = font_big
        self.font_small = font_small
        self.buttons: list[Button] = []
        w, h = 240, 56
        spacing = 18
        start_y = screen_rect.centery - 3 * (h + spacing) / 2
        labels = ["Play", "Inventory", "Shop", "Settings", "Exit"]
        for i, label in enumerate(labels):
            rect = pygame.Rect(screen_rect.centerx - w // 2, int(start_y + i * (h + spacing)), w, h)
            self.buttons.append(Button(rect, label, font_small, lambda l=label: self._route(l)))

    def _route(self, label: str) -> None:
        mapping = {
            "Play": "mode_select",
            "Inventory": "inventory",
            "Shop": "shop",
            "Settings": "settings",
            "Exit": "exit",
        }
        target = mapping.get(label)
        if target == "exit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif target:
            if target == "settings":
                settings_scene = self.manager.scenes.get("settings")
                if hasattr(settings_scene, "set_return_scene"):
                    settings_scene.set_return_scene("title")
            self.manager.set_scene(target)
            logger.info("Title route", extra={"target": target})

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)
        logger.debug("Title event", extra={"event": event.type})

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((10, 14, 22))
        title = self.font_big.render("BATTLE PONG", True, (255, 200, 120))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 100))
        for b in self.buttons:
            b.draw(screen)


class ModeSelectScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.buttons: list[Button] = []
        w, h = 260, 52
        spacing = 14
        base_y = 180
        opts = [
            ("Singleplayer", "play_menu"),
            ("Multiplayer (coming soon)", None),
            ("Zurück", "title"),
        ]
        for i, (label, target) in enumerate(opts):
            rect = pygame.Rect(160, base_y + i * (h + spacing), w, h)
            self.buttons.append(Button(rect, label, font_small, lambda t=target: self._select(t)))

    def _select(self, target: str | None) -> None:
        if target is None:
            return
        self.manager.set_scene(target)

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((16, 20, 30))
        title = self.font.render("Spielmodus", True, (230, 230, 240))
        screen.blit(title, (80, 100))
        for b in self.buttons:
            b.draw(screen)
