"\"\"\"Application entrypoint with SceneManager.\"\"\""

from __future__ import annotations

import logging
import pygame

from pong.abilities import ABILITY_SPECS, DEFAULT_ABILITY_ID, ability_inventory_items
from pong.events import EventBus, GameEvent, KeyAction
from pong.scenes import SceneManager, TitleScene, SettingsScene, PlayScene, PauseScene, ShopScene, InventoryScene
from pong.scenes.transitions import TransitionController, TransitionSpec
from pong.settings import RuntimeSettings
from pong.core.clock import Clock
from pong.core.input import InputState, Action, build_keymap_from_actions, default_action_keys
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

        # load persisted input config
        self.input_cfg = load_json("data/input_bindings.json", {})
        self.settings_cfg = load_json("data/settings.json", {})

        self.disp = self.settings.display
        # bump default window a bit larger
        self.settings.display.width = 1280
        self.settings.display.height = 720
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
        self.theme_cfg = load_json("data/theme.json", {})
        self.theme = self._build_theme_default()

        # economy state
        self.credits = 0
        self.owned_items: dict[str, set[str]] = {}
        self.ability_specs = ABILITY_SPECS
        self.loadout: dict[str, str] = {}

        self.skins = SkinRegistry(Path("skins"))
        self._skin_names = self.skins.list()
        self._skin_index = 0
        self._load_wallet()
        self._load_owned_items()
        self._load_loadout()
        self.inventory = self._load_inventory()
        self.ball_skins = self._load_ball_skins()
        self.ball_skin_index = 0
        self.paddle_skins = self._load_paddle_skins()
        self.paddle_skin_index = 0

        self.manager = SceneManager()
        self.manager.app = self
        # forward all events to current scene hook
        self.bus.subscribe(GameEvent, self.manager.handle_game_event)
        self.transitions = TransitionController()
        rect = self.screen.get_rect()
        self.log.info("Registering scenes...")
        self.manager.register("title", TitleScene(self.manager, rect, self.font_big, self.font, self.theme))
        self.manager.register("settings", SettingsScene(self.manager, self.font, self.font_small, self.theme))
        self.manager.register("play", PlayScene(self.manager, self.font, self.font_small))
        self.manager.register("pause", PauseScene(self.manager, self.font, self.font_small, self.theme))
        self.manager.register("shop", ShopScene(self.manager, self.font, self.font_small, self.theme))
        self.manager.register("inventory", InventoryScene(self.manager, self.font, self.font_small, self.theme))
        # share app context with scenes that need global flags
        self.manager.app_ctx = {
            "in_game": self.in_game,
            "palette": self.palette,
            "credits": self.credits,
            "owned_items": self.owned_items,
            "skin_names": self._skin_names,
            "play_area": (self.disp.width, self.disp.height),
            "ball_skins": self.ball_skins,
            "ball_skin_name": None,
            "ball_image": None,
            "paddle_skins": self.paddle_skins,
            "paddle_skin_name": None,
            "paddle_image": None,
            "inventory": self.inventory,
            "ability_specs": self.ability_specs,
            "loadout": self.loadout,
            "equipped_ability_id": self.loadout.get("ability"),
            "equipped_ability_name": self._ability_name(self.loadout.get("ability")),
            "ability_cooldown_remaining": 0.0,
            "ability_active_remaining": 0.0,
        }
        self.log.info("Applying initial skin...")
        if self._skin_names:
            self._apply_skin(self._skin_names[self._skin_index])
        if self.ball_skins:
            self._apply_ball_skin(self.ball_skin_index)
        if self.paddle_skins:
            self._apply_paddle_skin(self.paddle_skin_index)

        # Initial scene without transition to avoid blank screen
        self.log.info("Setting initial scene 'title' (no transition)...")
        self.manager.set_scene("title")
        self._configure_transitions()
        self.log.info("GameApp initialized; starting at 'title'")

        self.input = InputState(keymap=self._build_keymap())
        self.debug_overlay = DebugOverlay(
            DebugOverlayConfig(show=bool(self.settings_cfg.get("debug_overlay", False)))
        )
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

    def set_resolution(self, width: int, height: int) -> None:
        """Resolution change disabled; keep single window size."""
        return

    def _build_keymap(self):
        cfg = self.input_cfg if isinstance(self.input_cfg, dict) else {}
        actions = default_action_keys()
        for name, key in cfg.items():
            try:
                actions[name] = int(key)
            except Exception:
                continue
        return build_keymap_from_actions(actions)

    def save_input_cfg(self, action_keys: dict[str, int]) -> None:
        self.input_cfg = action_keys
        save_json("data/input_bindings.json", action_keys)

    def save_display_cfg(self) -> None:
        pass

    def set_debug_overlay_visible(self, visible: bool) -> None:
        show = bool(visible)
        if hasattr(self, "debug_overlay"):
            self.debug_overlay.config.show = show
        if not isinstance(self.settings_cfg, dict):
            self.settings_cfg = {}
        self.settings_cfg["debug_overlay"] = show
        save_json("data/settings.json", self.settings_cfg)

    def debug_overlay_visible(self) -> bool:
        if hasattr(self, "debug_overlay"):
            return bool(self.debug_overlay.config.show)
        if isinstance(self.settings_cfg, dict):
            return bool(self.settings_cfg.get("debug_overlay", False))
        return False

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
                        self.bus.publish(KeyAction(key=event.key, action="down", mods=event.mod))
                        if event.key == pygame.K_F5:
                            self.skins.refresh()
                            self._skin_names = self.skins.list()
                            self.manager.app_ctx["skin_names"] = self._skin_names
                            self.log.info("Skins refreshed", extra={"count": len(self._skin_names)})
                        elif event.key == pygame.K_F6 and self._skin_names:
                            self._skin_index = (self._skin_index + 1) % len(self._skin_names)
                            self._apply_skin(self._skin_names[self._skin_index])
                            self.log.info("Skin cycled", extra={"skin": self._skin_names[self._skin_index]})
                        elif event.key == pygame.K_F7 and self.ball_skins:
                            self.ball_skin_index = (self.ball_skin_index + 1) % len(self.ball_skins)
                            self._apply_ball_skin(self.ball_skin_index)
                            self.log.info("Ball skin cycled", extra={"ball_skin": self.ball_skins[self.ball_skin_index]})
                        elif event.key == pygame.K_F8 and self.ball_skins:
                            self.ball_skin_index = (self.ball_skin_index - 1) % len(self.ball_skins)
                            self._apply_ball_skin(self.ball_skin_index)
                            self.log.info("Ball skin cycled", extra={"ball_skin": self.ball_skins[self.ball_skin_index]})
                        elif event.key == pygame.K_F9 and self.paddle_skins:
                            self.paddle_skin_index = (self.paddle_skin_index + 1) % len(self.paddle_skins)
                            self._apply_paddle_skin(self.paddle_skin_index)
                            self.log.info("Paddle skin cycled", extra={"paddle_skin": self.paddle_skins[self.paddle_skin_index]})
                    elif event.type == pygame.KEYUP:
                        self.bus.publish(KeyAction(key=event.key, action="up", mods=event.mod))

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
            self.manager.app_ctx["owned_items"] = self.owned_items
            self.manager.app_ctx["skin_names"] = self._skin_names
            self.manager.app_ctx["play_area"] = (self.disp.width, self.disp.height)
            self.manager.app_ctx["ball_skins"] = self.ball_skins
            self.manager.app_ctx["ball_skin_name"] = (
                self.ball_skins[self.ball_skin_index] if self.ball_skins else None
            )
            self.manager.app_ctx["paddle_skins"] = self.paddle_skins
            self.manager.app_ctx["paddle_skin_name"] = (
                self.paddle_skins[self.paddle_skin_index] if self.paddle_skins else None
            )
            self.manager.app_ctx["inventory"] = self.inventory
            self.manager.app_ctx["loadout"] = self.loadout
            self.manager.app_ctx["equipped_ability_id"] = self.loadout.get("ability")
            self.manager.app_ctx["equipped_ability_name"] = self._ability_name(self.loadout.get("ability"))

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
            f"ability: {self._ability_name(self.loadout.get('ability'))}",
        ]

    def _apply_skin(self, name: str) -> None:
        manifest = self.skins.apply(name)
        self.palette = manifest.palette
        # Keep UI theme from theme.json; do not override with palette to honor user colors.
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

    def _load_owned_items(self) -> None:
        data = load_json(
            "data/owned_items.json",
            {"ball": [], "paddle": [], "ability": list(self._default_owned_items()["ability"])},
        )
        owned: dict[str, set[str]] = {}
        for cat, lst in data.items():
            if isinstance(lst, list):
                owned[cat] = set(map(str, lst))
        for cat, defaults in self._default_owned_items().items():
            owned.setdefault(cat, set()).update(defaults)
        self.owned_items = owned
        if hasattr(self, "manager") and hasattr(self.manager, "app_ctx"):
            self.manager.app_ctx["owned_items"] = self.owned_items

    def _save_owned_items(self) -> None:
        save_json("data/owned_items.json", {k: list(v) for k, v in self.owned_items.items()})

    def _load_loadout(self) -> None:
        data = load_json("data/loadout.json", {})
        if not isinstance(data, dict):
            data = {}
        loadout = {k: str(v) for k, v in data.items() if v is not None}
        ability_id = loadout.get("ability", DEFAULT_ABILITY_ID)
        if ability_id not in self.ability_specs:
            ability_id = DEFAULT_ABILITY_ID
        loadout["ability"] = ability_id
        self.loadout = loadout

    def _save_loadout(self) -> None:
        save_json("data/loadout.json", self.loadout)

    def set_equipped_ability(self, ability_id: str) -> bool:
        if ability_id not in self.ability_specs:
            return False
        self.loadout["ability"] = ability_id
        self._save_loadout()
        if hasattr(self, "manager") and hasattr(self.manager, "app_ctx"):
            self.manager.app_ctx["loadout"] = self.loadout
            self.manager.app_ctx["equipped_ability_id"] = ability_id
            self.manager.app_ctx["equipped_ability_name"] = self._ability_name(ability_id)
        return True

    def _load_inventory(self) -> dict:
        data = load_json("data/inventory.json", {"categories": []})
        cats = data.get("categories", []) if isinstance(data, dict) else []
        categories = []
        for c in cats:
            cid = c.get("id")
            label = c.get("label", cid)
            price = int(c.get("default_price", 0)) if cid else 0
            items = []
            raw_items = c.get("items", []) if isinstance(c, dict) else []
            for itm in raw_items:
                path = itm.get("path")
                item_id = itm.get("id") or (Path(path).stem if path else None)
                if not item_id:
                    continue
                items.append(
                    {
                        "id": item_id,
                        "name": itm.get("name") or (Path(path).stem.replace("_", " ").title() if path else str(item_id).replace("_", " ").title()),
                        "path": path,
                        "price": int(itm.get("price", price)),
                        "rarity": itm.get("rarity", "common"),
                        "description": itm.get("description", ""),
                        "cooldown": float(itm.get("cooldown", 0.0)),
                        "duration": float(itm.get("duration", 0.0)),
                    }
                )
            if cid:
                categories.append({"id": cid, "label": label, "default_price": price, "items": items})
        categories = [c for c in categories if c.get("id") != "ability"]
        categories.append(
            {
                "id": "ability",
                "label": "Abilities",
                "default_price": 0,
                "items": ability_inventory_items(),
            }
        )
        self.log.info(
            "Inventory categories loaded",
            extra={
                "count": len(categories),
                "items": {c["id"]: len(c.get("items", [])) for c in categories},
            },
        )
        return {"categories": categories}

    def _default_owned_items(self) -> dict[str, set[str]]:
        return {
            "ability": set(self.ability_specs.keys()),
        }

    def _ability_name(self, ability_id: str | None) -> str:
        if not ability_id:
            return "None"
        spec = self.ability_specs.get(ability_id)
        return spec.name if spec else ability_id

    # ball skins -------------------------------------------------------- #
    def _load_ball_skins(self) -> list[str]:
        base = Path("skins/ball")
        if not base.exists():
            return []
        files = sorted([str(p) for p in base.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}])
        self.log.info("Ball skins discovered", extra={"count": len(files)})
        return files

    def _load_paddle_skins(self) -> list[str]:
        base = Path("skins/paddle")
        if not base.exists():
            return []
        files = sorted([str(p) for p in base.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}])
        self.log.info("Paddle skins discovered", extra={"count": len(files)})
        return files

    def _apply_ball_skin(self, index: int) -> None:
        if not self.ball_skins:
            return
        idx = index % len(self.ball_skins)
        path = self.ball_skins[idx]
        try:
            surf = pygame.image.load(path).convert_alpha()
            self.manager.app_ctx["ball_image"] = surf
            self.ball_skin_index = idx
            self.manager.app_ctx["ball_skin_name"] = path
            self.log.info("Ball skin applied", extra={"path": path, "index": idx})
        except Exception as exc:
            self.log.warning("Failed to load ball skin", extra={"path": path, "error": str(exc)})

    def _apply_paddle_skin(self, index: int) -> None:
        if not self.paddle_skins:
            return
        idx = index % len(self.paddle_skins)
        path = self.paddle_skins[idx]
        try:
            surf = pygame.image.load(path).convert_alpha()
            self.manager.app_ctx["paddle_image"] = surf
            self.paddle_skin_index = idx
            self.manager.app_ctx["paddle_skin_name"] = path
            self.log.info("Paddle skin applied", extra={"path": path, "index": idx})
        except Exception as exc:
            self.log.warning("Failed to load paddle skin", extra={"path": path, "error": str(exc)})

    def _build_theme_default(self) -> ThemeTokens:
        cfg = self.theme_cfg
        def get(section: str, key: str, default: str) -> str:
            return cfg.get(section, {}).get(key, default) if isinstance(cfg, dict) else default
        def get_int(section: str, key: str, default: int) -> int:
            try:
                return int(cfg.get(section, {}).get(key, default))
            except Exception:
                return default

        primary = ButtonStyle(
            base=_hex_to_rgb(get("primary", "base", "#1c202c")),
            hover=_hex_to_rgb(get("primary", "hover", "#4a6ebe")),
            press=_hex_to_rgb(get("primary", "press", "#141824")),
            border=_hex_to_rgb(get("primary", "border", "#f0f0ff")),
            text=_hex_to_rgb(get("primary", "text", "#fafaff")),
            radius=get_int("primary", "radius", 12),
        )
        ghost = ButtonStyle(
            base=_hex_to_rgb(get("ghost", "base", "#0f1116")),
            hover=_hex_to_rgb(get("ghost", "hover", "#2c3650")),
            press=_hex_to_rgb(get("ghost", "press", "#0a0c10")),
            border=_hex_to_rgb(get("ghost", "border", "#aabedc")),
            text=_hex_to_rgb(get("ghost", "text", "#dce4f5")),
            radius=get_int("ghost", "radius", 12),
        )
        return ThemeTokens(variants={"primary": primary, "ghost": ghost})

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
