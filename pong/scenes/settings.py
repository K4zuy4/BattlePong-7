from __future__ import annotations

import pygame
import logging
import sys
from pathlib import Path

# Allow running as script
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    __package__ = "pong.scenes"

from ..data_io import load_json, save_json
from ..events import SettingsChangeRequested
from .base import Scene, SceneManager
from ..ui.widgets import Button, Label

logger = logging.getLogger(__name__)


class SettingsScene(Scene):
    def __init__(self, manager: SceneManager, bus, settings, font, font_small) -> None:
        self.manager = manager
        self.bus = bus
        self.settings = settings
        self.font = font
        self.font_small = font_small
        self.return_scene = "title"
        self.data_path = "data/settings.json"
        self.data = load_json(
            self.data_path,
            {"master_volume": 1.0, "sfx_volume": 1.0, "screen_shake": 0.5},
        )
        self.labels = [
            Label("Master Volume: +/-", (40, 140), font_small),
            Label("SFX Volume: +/-", (40, 180), font_small),
            Label("Screen Shake: +/-", (40, 220), font_small),
        ]
        self.buttons = [
            Button(pygame.Rect(40, 280, 160, 44), "Apply", font_small, self._apply),
            Button(pygame.Rect(220, 280, 160, 44), "Zurück", font_small, self._back),
        ]

    def set_return_scene(self, name: str) -> None:
        self.return_scene = name

    def _apply(self) -> None:
        save_json(self.data_path, self.data)
        self.bus.publish(
            SettingsChangeRequested(
                section="audio",
                values={
                    "master_volume": self.data["master_volume"],
                    "sfx_volume": self.data["sfx_volume"],
                    "screen_shake": self.data["screen_shake"],
                },
            )
        )
        self.manager.set_scene(self.return_scene)
        logger.info("Settings applied", extra={"data": self.data})

    def _back(self) -> None:
        self.manager.set_scene(self.return_scene)
        logger.debug("Settings back", extra={"return_scene": self.return_scene})

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.data["master_volume"] = min(1.0, self.data["master_volume"] + 0.1)
            elif event.key == pygame.K_MINUS:
                self.data["master_volume"] = max(0.0, self.data["master_volume"] - 0.1)
            elif event.key == pygame.K_q:
                self.data["sfx_volume"] = max(0.0, self.data["sfx_volume"] - 0.1)
            elif event.key == pygame.K_w:
                self.data["sfx_volume"] = min(1.0, self.data["sfx_volume"] + 0.1)
            elif event.key == pygame.K_a:
                self.data["screen_shake"] = max(0.0, self.data["screen_shake"] - 0.1)
            elif event.key == pygame.K_s:
                self.data["screen_shake"] = min(1.0, self.data["screen_shake"] + 0.1)
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((16, 20, 28))
        title = self.font.render("Settings", True, (230, 230, 230))
        screen.blit(title, (40, 40))
        values = [
            f"{self.data['master_volume']:.1f}",
            f"{self.data['sfx_volume']:.1f}",
            f"{self.data['screen_shake']:.1f}",
        ]
        for label, val in zip(self.labels, values):
            label.draw(screen)
            val_img = self.font_small.render(val, True, (180, 255, 200))
            screen.blit(val_img, (280, label.pos[1]))
        for b in self.buttons:
            b.draw(screen)
