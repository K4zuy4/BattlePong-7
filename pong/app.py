"\"\"\"Application entrypoint with SceneManager.\"\"\""

from __future__ import annotations

import pygame

from pong.events import EventBus
from pong.scenes import (
    InventoryScene,
    ModeSelectScene,
    PauseScene,
    PlayMenuScene,
    PlayScene,
    SceneManager,
    SettingsScene,
    ShopScene,
    TitleScene,
)
from pong.settings import RuntimeSettings


class GameApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()

        self.settings = RuntimeSettings()
        self.bus = EventBus()

        disp = self.settings.display
        self.screen = pygame.display.set_mode((disp.width, disp.height))
        pygame.display.set_caption(disp.title)
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_big = pygame.font.SysFont("consolas", 48, bold=True)
        self.font = pygame.font.SysFont("consolas", 34, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 24)

        self.ctx: dict = {"bot_difficulty": "easy"}

        self.manager = SceneManager()
        rect = self.screen.get_rect()
        self.manager.register("title", TitleScene(self.manager, rect, self.font_big, self.font))
        self.manager.register("mode_select", ModeSelectScene(self.manager, self.font, self.font_small))
        self.manager.register("play_menu", PlayMenuScene(self.manager, self.ctx, self.font, self.font_small))
        play_scene = PlayScene(self.manager, self.ctx, self.bus, self.settings, self.screen)
        self.manager.register("play", play_scene)
        self.manager.register("pause", PauseScene(self.manager, play_scene, self.font, self.font_small))
        self.manager.register("inventory", InventoryScene(self.manager, self.bus, self.ctx, self.font, self.font_small))
        self.manager.register("shop", ShopScene(self.manager, self.font, self.font_small))
        self.manager.register("settings", SettingsScene(self.manager, self.bus, self.settings, self.font, self.font_small))

        self.manager.set_scene("title")

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.settings.display.fps) / 1000.0
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.manager.handle_event(event)
            self.manager.update(dt)
            self.manager.draw(self.screen)
            pygame.display.flip()

        pygame.quit()


def run() -> None:
    GameApp().run()
