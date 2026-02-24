"\"\"\"Application entrypoint with SceneManager.\"\"\""

from __future__ import annotations

import logging
import pygame

from pong.events import EventBus
from pong.scenes import SceneManager, TitleScene, SettingsScene, PlayScene, PauseScene, SkinsScene, ShopScene
from pong.scenes.transitions import TransitionController, TransitionSpec
from pong.settings import RuntimeSettings
from pong.core.clock import Clock
from pong.core.input import InputState, Action
from pong.core.debug import DebugOverlay, DebugOverlayConfig
from pong.skin import SkinRegistry
from pathlib import Path
from pong.ui.widgets import ThemeTokens, ButtonStyle
from pong.data_io import load_json, save_json


class GameApp:
    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)
        self.headless = False
        try:
            pygame.init()
            pygame.font.init()
            self.log.debug("Pygame initialized")
        except Exception as exc:
            self.log.warning("Pygame init failed", extra={"error": str(exc)})


        self.settings = RuntimeSettings()
        self.bus = EventBus()
        self.log.debug("RuntimeSettings and EventBus created")

        self.disp = self.settings.display
        self.screen = self._init_display(self.disp.width, self.disp.height, self.disp.title)
        self.clock = Clock()
        self.running = True

        self.font_big = pygame.font.SysFont("consolas", 48, bold=True)
        self.font = pygame.font.SysFont("consolas", 34, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 24)

        # game state flag
        self.in_game = False
        self.palette = None
        self.theme = self._build_theme_default()

        # economy state
        self.credits = 0
        self.owned_skins: set[str] = set()

        self.skins = SkinRegistry(Path("skins"))
        self._skin_names = self.skins.list()
        self._skin_index = 0
        self._load_wallet()
        self._load_owned_skins()

        self.manager = SceneManager()
        self.manager.app = self
        self.transitions = TransitionController()
        rect = self.screen.get_rect()
        self.log.info("Registering scenes...")
        self.manager.register("title", TitleScene(self.manager, rect, self.font_big, self.font, self.theme))
        self.manager.register("settings", SettingsScene(self.manager, self.font, self.font_small, self.theme))
        self.manager.register("play", PlayScene(self.manager, self.font, self.font_small))
        self.manager.register("pause", PauseScene(self.manager, self.font, self.font_small, self.theme))
        self.manager.register("skins", SkinsScene(self.manager, self.font, self.font_small, self.theme))
        self.manager.register("shop", ShopScene(self.manager, self.font, self.font_small, self.theme))
        # share app context with scenes that need global flags
        self.manager.app_ctx = {
            "in_game": self.in_game,
            "palette": self.palette,
            "credits": self.credits,
            "owned_skins": self.owned_skins,
            "skin_names": self._skin_names,
        }
        self.log.info("Applying initial skin...")
        if self._skin_names:
            self._apply_skin(self._skin_names[self._skin_index])

        # Initial scene without transition to avoid blank screen
        self.log.info("Setting initial scene 'title' (no transition)...")
        self.manager.set_scene("title")
        self._configure_transitions()
        self.log.info("GameApp initialized; starting at 'title'")

        self.input = InputState()
        self.debug_overlay = DebugOverlay(DebugOverlayConfig())
        self.debug_overlay.set_provider(self._debug_lines)


    def _init_display(self, width: int, height: int, title: str):
        """Init display; fail fast with clear hint unless explicit headless opt-in."""
        import os
        allow_headless = os.environ.get("ALLOW_HEADLESS") == "1"
        try:
            screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(title)
            self.headless = False
            self.log.info("Using video driver %s", pygame.display.get_driver())
            return screen
        except pygame.error as exc:
            if not allow_headless:
                msg = (
                    "No video device available. To run headless set ALLOW_HEADLESS=1 SDL_VIDEODRIVER=dummy, "
                    f"or start with a real display (DISPLAY/Wayland). Original error: {exc}"
                )
                self.log.error(msg)
                raise SystemExit(msg)
            self.log.warning("No video device, using dummy driver (ALLOW_HEADLESS=1)", extra={"error": str(exc)})
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(title + " (headless)")
            self.headless = True
            return screen

    def _configure_transitions(self) -> None:
        def provider() -> TransitionSpec:
            return TransitionSpec(name="fade", duration=0.25, easing="linear", color=(0, 0, 0))

        self.manager.attach_transitions(self.transitions, provider)

    def run(self) -> None:
        self.log.info("Entering main loop")
        while self.running:
            self.clock.tick(self.disp.fps)
            self.log.debug("Frame tick", extra={"fps": self.clock.fps, "scene": self.manager.current_name})

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
                            self.manager.app_ctx["skin_names"] = self._skin_names
                            self.log.info("Skins refreshed", extra={"count": len(self._skin_names)})
                        elif event.key == pygame.K_F6 and self._skin_names:
                            self._skin_index = (self._skin_index + 1) % len(self._skin_names)
                            self._apply_skin(self._skin_names[self._skin_index])
                            self.log.info("Skin cycled", extra={"skin": self._skin_names[self._skin_index]})

            # global actions
            pressed_back = self.input.consume(Action.BACK)
            pressed_pause = self.input.consume(Action.PAUSE)
            current = self.manager.current_name
            self.log.debug("Input processed", extra={"back": pressed_back, "pause": pressed_pause, "scene": current})

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
            self.manager.app_ctx["credits"] = self.credits
            self.manager.app_ctx["owned_skins"] = self.owned_skins
            self.manager.app_ctx["skin_names"] = self._skin_names

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

        self.log.info("Main loop exited")
        pygame.quit()
        self.log.info("Game loop exited")

    def _debug_lines(self) -> list[str]:
        return [
            f"fps: {self.clock.fps:.1f}",
            f"scene: {self.manager.current_name}",
            f"transition: {'on' if self.transitions.active else 'off'}",
            f"skin: {self.skins.active if self.skins.active else 'none'}",
            f"in_game: {self.in_game}",
            f"credits: {self.credits}",
        ]

    def _apply_skin(self, name: str) -> None:
        manifest = self.skins.apply(name)
        self.palette = manifest.palette
        self._update_theme_from_palette(self.palette)
        self.manager.app_ctx["palette"] = self.palette
        # load optional assets
        self._load_skin_assets(manifest)
        self.log.info("Skin applied", extra={"skin": manifest.name})

    def _update_game_flag(self) -> None:
        current = self.manager.current_name
        if current == "play":
            self.in_game = True
        elif current == "title":
            self.in_game = False

    # economy ----------------------------------------------------------- #
    def _load_wallet(self) -> None:
        data = load_json("data/wallet.json", {"credits": 0})
        self.credits = int(data.get("credits", 0))
        if hasattr(self, "manager") and hasattr(self.manager, "app_ctx"):
            self.manager.app_ctx["credits"] = self.credits

    def _save_wallet(self) -> None:
        save_json("data/wallet.json", {"credits": self.credits})

    def _load_owned_skins(self) -> None:
        data = load_json("data/skins_owned.json", [])
        if isinstance(data, list):
            self.owned_skins = set(map(str, data))
        else:
            self.owned_skins = set()
        if hasattr(self, "manager") and hasattr(self.manager, "app_ctx"):
            self.manager.app_ctx["owned_skins"] = self.owned_skins

    def _save_owned_skins(self) -> None:
        save_json("data/skins_owned.json", list(self.owned_skins))

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

    def _load_skin_assets(self, manifest) -> None:
        bg_image = None
        path = manifest.assets.get("bg") if hasattr(manifest, "assets") else None
        if path:
            try:
                surf = pygame.image.load(path).convert()
                bg_image = pygame.transform.scale(surf, (self.disp.width, self.disp.height))
            except Exception as exc:
                self.log.warning("Failed to load background image", extra={"path": path, "error": str(exc)})
                bg_image = None
        self.manager.app_ctx["bg_image"] = bg_image

        ball_img = None
        ball_path = manifest.assets.get("ball") if hasattr(manifest, "assets") else None
        if ball_path:
            try:
                ball_img = pygame.image.load(ball_path).convert_alpha()
            except Exception as exc:
                self.log.warning("Failed to load ball image", extra={"path": ball_path, "error": str(exc)})
                ball_img = None
        self.manager.app_ctx["ball_image"] = ball_img

        paddle_img = None
        paddle_path = manifest.assets.get("paddle") if hasattr(manifest, "assets") else None
        if paddle_path:
            try:
                paddle_img = pygame.image.load(paddle_path).convert_alpha()
            except Exception as exc:
                self.log.warning("Failed to load paddle image", extra={"path": paddle_path, "error": str(exc)})
                paddle_img = None
        self.manager.app_ctx["paddle_image"] = paddle_img

def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))


def _tint(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def run() -> None:
    GameApp().run()
