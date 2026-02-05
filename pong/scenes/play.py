from __future__ import annotations

import pygame
import logging

try:
    from ..game import PongGame
    from .base import Scene, SceneManager
    from ..ui.widgets import Button
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from pong.game import PongGame
    from pong.scenes.base import Scene, SceneManager
    from pong.ui.widgets import Button

logger = logging.getLogger(__name__)


class PlayScene(Scene):
    def __init__(self, manager: SceneManager, app_ctx: dict, bus, settings, screen) -> None:
        self.manager = manager
        self.app_ctx = app_ctx
        self.bus = bus
        self.settings = settings
        self.screen = screen
        self.game: PongGame | None = None

    def on_enter(self) -> None:
        bot = self.app_ctx.get("bot_difficulty", "easy")
        if self.game is None:
            self.game = PongGame(bus=self.bus, settings=self.settings, screen=self.screen, bot_mode=bot)
        else:
            self.game.bot_mode = bot
        logger.info("PlayScene enter", extra={"bot_mode": bot})

    def reset_game(self) -> None:
        self.game = None
        logger.debug("PlayScene reset game")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.manager.set_scene("pause")

    def update(self, dt: float) -> None:
        if self.game:
            self.game.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        if self.game:
            self.game.draw()


class PauseScene(Scene):
    def __init__(self, manager: SceneManager, play_scene: PlayScene, font, font_small) -> None:
        self.manager = manager
        self.play_scene = play_scene
        self.font = font
        self.font_small = font_small
        self.buttons = [
            Button(pygame.Rect(60, 180, 200, 48), "Resume", font_small, lambda: manager.set_scene("play")),
            Button(pygame.Rect(60, 240, 200, 48), "Settings", font_small, self._open_settings),
            Button(pygame.Rect(60, 300, 200, 48), "Quit to Title", font_small, self._quit_to_title),
        ]

    def _open_settings(self) -> None:
        settings_scene = self.manager.scenes.get("settings")
        if hasattr(settings_scene, "set_return_scene"):
            settings_scene.set_return_scene("pause")
        self.manager.set_scene("settings")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.manager.set_scene("play")
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        if self.play_scene.game:
            self.play_scene.game.draw()
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        title = self.font.render("Paused", True, (255, 255, 255))
        screen.blit(title, (60, 120))
        for b in self.buttons:
            b.draw(screen)

    def _quit_to_title(self) -> None:
        if hasattr(self.play_scene, "reset_game"):
            self.play_scene.reset_game()
        self.manager.set_scene("title")
        logger.info("Quit to title from pause")
