"\"\"\"Application entrypoint with SceneManager.\"\"\""

from __future__ import annotations

import logging
import pygame

from pong.events import EventBus
from pong.scenes import SceneManager, TitleScene, SettingsScene, PlayScene, PauseScene
from pong.scenes.transitions import TransitionController, TransitionSpec
from pong.settings import RuntimeSettings
from pong.core.clock import Clock
from pong.core.input import InputState, Action
from pong.core.debug import DebugOverlay, DebugOverlayConfig
from pong.skin import SkinRegistry
from pathlib import Path
from pong.ui.widgets import ThemeTokens, ButtonStyle


class GameApp:
    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)
        pygame.init()
        pygame.font.init()
        self.log.debug("Pygame initialized")

        self.settings = RuntimeSettings()
        self.bus = EventBus()
        self.log.debug("RuntimeSettings and EventBus created")

        self.disp = self.settings.display
        self.screen = pygame.display.set_mode((self.disp.width, self.disp.height))
        pygame.display.set_caption(self.disp.title)
        self.clock = Clock()
        self.running = True

        self.font_big = pygame.font.SysFont("consolas", 48, bold=True)
        self.font = pygame.font.SysFont("consolas", 34, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 24)

        # game state flag
        self.in_game = False
        self.palette = None
        self.theme = self._build_theme_default()

        self.manager = SceneManager()
        self.transitions = TransitionController()
        rect = self.screen.get_rect()
        self.manager.register("title", TitleScene(self.manager, rect, self.font_big, self.font, self.theme))
        self.manager.register("settings", SettingsScene(self.manager, self.font, self.font_small, self.theme))
        self.manager.register("play", PlayScene(self.manager, self.font, self.font_small))
        self.manager.register("pause", PauseScene(self.manager, self.font, self.font_small, self.theme))
        # share app context with scenes that need global flags
        self.manager.app_ctx = {"in_game": self.in_game, "palette": self.palette}
        self._configure_transitions()
        self.manager.set_scene("title")
        self.log.info("GameApp initialized; starting at 'title'")

        self.input = InputState()
        self.debug_overlay = DebugOverlay(DebugOverlayConfig())
        self.debug_overlay.set_provider(self._debug_lines)

        self.skins = SkinRegistry(Path("skins"))
        self._skin_names = self.skins.list()
        self._skin_index = 0
        if self._skin_names:
            self._apply_skin(self._skin_names[self._skin_index])

        self.in_game = False

    def _configure_transitions(self) -> None:
        def provider() -> TransitionSpec:
            return TransitionSpec(name="fade", duration=0.25, easing="linear", color=(0, 0, 0))

        self.manager.attach_transitions(self.transitions, provider)

    def run(self) -> None:
        while self.running:
            self.clock.tick(self.disp.fps)
            self.log.debug("Frame tick", extra={"fps": self.clock.fps})

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    self.log.info("Quit event received")
                else:
                    self.input.process_event(event)
                    self.manager.handle_event(event)
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_F5:
                            self.skins.refresh()
                            self._skin_names = self.skins.list()
                        elif event.key == pygame.K_F6 and self._skin_names:
                            self._skin_index = (self._skin_index + 1) % len(self._skin_names)
                            self._apply_skin(self._skin_names[self._skin_index])

            # global actions
            pressed_back = self.input.consume(Action.BACK)
            pressed_pause = self.input.consume(Action.PAUSE)
            current = self.manager.current_name

            if current == "pause":
                if pressed_pause or pressed_back:
                    self.manager.pop()
            elif current == "settings":
                if pressed_back:
                    if self.in_game:
                        self.manager.pop()
                    else:
                        self.manager.set_scene("title")
            elif current == "play":
                if pressed_pause or pressed_back:
                    self.manager.push("pause")
            else:
                if pressed_back and not self.in_game:
                    self.manager.set_scene("title")

            self.manager.handle_input(self.input)

            # update game state flag after potential scene changes
            self._update_game_flag()
            self.manager.app_ctx["in_game"] = self.in_game

            # Fixed-step updates
            while self.clock.step_ready():
                fixed_dt = self.clock.consume_step()
                self.manager.update(fixed_dt)
                self.transitions.update(fixed_dt)

            # Render pass
            self.manager.draw(self.screen)
            self.transitions.draw_overlay(self.screen)
            self.debug_overlay.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
        self.log.info("Game loop exited")

    def _debug_lines(self) -> list[str]:
        return [
            f"fps: {self.clock.fps:.1f}",
            f"scene: {self.manager.current_name}",
            f"transition: {'on' if self.transitions.active else 'off'}",
            f"skin: {self.skins.active if self.skins.active else 'none'}",
            f"in_game: {self.in_game}",
        ]

    def _apply_skin(self, name: str) -> None:
        manifest = self.skins.apply(name)
        self.palette = manifest.palette
        self._update_theme_from_palette(self.palette)
        self.manager.app_ctx["palette"] = self.palette
        self.log.info("Skin applied", extra={"skin": manifest.name})

    def _update_game_flag(self) -> None:
        current = self.manager.current_name
        if current == "play":
            self.in_game = True
        elif current == "title":
            self.in_game = False

    def _build_theme_default(self) -> ThemeTokens:
        return ThemeTokens(
            variants={
                "primary": ButtonStyle(
                    base=(64, 78, 120),
                    hover=(90, 112, 168),
                    press=(52, 62, 96),
                    border=(220, 230, 255),
                    text=(255, 255, 255),
                    radius=12,
                ),
                "ghost": ButtonStyle(
                    base=(28, 32, 44),
                    hover=(40, 46, 64),
                    press=(22, 26, 36),
                    border=(140, 160, 200),
                    text=(220, 230, 255),
                    radius=12,
                ),
            }
        )

    def _update_theme_from_palette(self, palette) -> None:
        if palette is None:
            return
        primary_base = _hex_to_rgb(palette.primary)
        accent = _hex_to_rgb(palette.accent)
        fg = _hex_to_rgb(palette.foreground)
        ghost_base = _hex_to_rgb(palette.background)
        self.theme.variants["primary"] = ButtonStyle(
            base=primary_base,
            hover=_tint(primary_base, 1.1),
            press=_tint(primary_base, 0.9),
            border=_tint(fg, 1.0),
            text=fg,
            radius=12,
        )
        self.theme.variants["ghost"] = ButtonStyle(
            base=ghost_base,
            hover=_tint(ghost_base, 1.05),
            press=_tint(ghost_base, 0.95),
            border=_tint(accent, 1.0),
            text=fg,
            radius=12,
        )


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))


def _tint(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def run() -> None:
    GameApp().run()
