"""Scene system for menus and game flow."""

from __future__ import annotations

import pygame

from pong.game import PongGame
from pong.data_io import load_json, save_json
from pong.events import SettingsChangeRequested, SpawnBallRequested
from pong.ui.widgets import Button, Label


class Scene:
    def handle_event(self, event: pygame.event.Event) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        raise NotImplementedError

    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass


class SceneManager:
    def __init__(self) -> None:
        self.scenes: dict[str, Scene] = {}
        self.current: str | None = None
        self._history: list[str] = []

    def register(self, name: str, scene: Scene) -> None:
        self.scenes[name] = scene

    def set_scene(self, name: str) -> None:
        if self.current == name:
            return
        if self.current:
            self.scenes[self.current].on_exit()
            self._history.append(self.current)
        self.current = name
        self.scenes[name].on_enter()

    def go_back(self) -> None:
        if not self._history:
            return
        prev = self._history.pop()
        if self.current:
            self.scenes[self.current].on_exit()
        self.current = prev
        self.scenes[self.current].on_enter()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.current:
            self.scenes[self.current].handle_event(event)

    def update(self, dt: float) -> None:
        if self.current:
            self.scenes[self.current].update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        if self.current:
            self.scenes[self.current].draw(screen)


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

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

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
            ("Multiplayer", None),
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


class PlayMenuScene(Scene):
    def __init__(self, manager: SceneManager, app_ctx: dict, font, font_small) -> None:
        self.manager = manager
        self.app_ctx = app_ctx
        self.font = font
        self.font_small = font_small
        self.buttons: list[Button] = []
        w, h = 280, 52
        spacing = 12
        base_y = 180
        opts = [
            ("Einfach", "easy"),
            ("Mittel", "medium"),
            ("Schwer", "hard"),
            ("KI", "ai"),
            ("Zurück", "title"),
        ]
        for i, (label, value) in enumerate(opts):
            rect = pygame.Rect(160, base_y + i * (h + spacing), w, h)
            self.buttons.append(Button(rect, label, font_small, lambda v=value: self._select(v)))

    def _select(self, value) -> None:
        if value is None:
            return
        if value == "title":
            self.manager.set_scene("mode_select")
            return
        self.app_ctx["bot_difficulty"] = value
        self.manager.set_scene("play")

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((20, 24, 36))
        title = self.font.render("Singleplayer Bots", True, (220, 220, 240))
        screen.blit(title, (80, 100))
        for b in self.buttons:
            b.draw(screen)


class InventoryScene(Scene):
    def __init__(self, manager: SceneManager, bus, app_ctx: dict, font, font_small) -> None:
        self.manager = manager
        self.bus = bus
        self.app_ctx = app_ctx
        self.font = font
        self.font_small = font_small
        self.inventory_path = "data/inventory.json"
        self.loadout_path = "data/loadout.json"
        self.data = load_json(self.inventory_path, {})
        self.loadout = load_json(self.loadout_path, {})
        self.categories = list(self.data.keys()) or ["paddle", "ball", "background", "trail", "animation"]
        self.current_cat_idx = 0
        self.buttons: list[Button] = []
        self.item_buttons: list[Button] = []
        self.status_msg = ""
        self._build_buttons()

    def on_enter(self) -> None:
        self.data = load_json(self.inventory_path, {})
        self.loadout = load_json(self.loadout_path, {})
        self.categories = list(self.data.keys()) or ["paddle", "ball", "background", "trail", "animation"]
        self.current_cat_idx = 0
        self.status_msg = ""
        self._build_buttons()

    def _build_buttons(self) -> None:
        self.buttons = []
        tab_w = 140
        for i, cat in enumerate(self.categories):
            rect = pygame.Rect(40 + i * (tab_w + 8), 80, tab_w, 40)
            self.buttons.append(Button(rect, cat.title(), self.font_small, lambda c=cat: self._set_category(c)))
        apply_rect = pygame.Rect(40, 400, 160, 44)
        back_rect = pygame.Rect(220, 400, 160, 44)
        self.buttons.append(Button(apply_rect, "Apply", self.font_small, self._apply))
        self.buttons.append(Button(back_rect, "Zurück", self.font_small, lambda: self.manager.set_scene("title")))
        self._build_items()

    def _set_category(self, cat: str) -> None:
        self.current_cat_idx = self.categories.index(cat)
        self._build_items()

    def _build_items(self) -> None:
        self.item_buttons = []
        items = self.data.get(self.categories[self.current_cat_idx], [])
        for i, item in enumerate(items[:8]):
            suffix = "" if item.get("unlocked", False) else " (locked)"
            rect = pygame.Rect(40, 150 + i * 50, 260, 40)
            self.item_buttons.append(
                Button(rect, f"{item.get('name','Item')} [{item.get('id','')}] {suffix}",
                       self.font_small, lambda it=item: self._select_item(it))
            )

    def _select_item(self, item: dict) -> None:
        cat = self.categories[self.current_cat_idx]
        if not item.get("unlocked", False):
            self.status_msg = "Locked. Kauf im Shop."
            return
        self.loadout[cat] = item.get("id")
        self.app_ctx.setdefault("selected_items", {})[cat] = item
        self.status_msg = f"Ausgewählt: {item.get('name','')}"

    def _apply(self) -> None:
        save_json(self.loadout_path, self.loadout)
        sel = self.app_ctx.get("selected_items", {})
        sprites: dict[str, str | None] = {}
        if "paddle" in sel:
            sprites["paddle_image"] = sel["paddle"].get("sprite")
        if "ball" in sel:
            sprites["ball_image"] = sel["ball"].get("sprite")
        if "background" in sel:
            sprites["background_image"] = sel["background"].get("sprite")
        if sprites:
            self.bus.publish(SettingsChangeRequested(section="sprites", values=sprites))
        self.manager.set_scene("title")

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)
        for b in self.item_buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((18, 18, 26))
        title = self.font.render("Inventory", True, (230, 230, 230))
        screen.blit(title, (40, 30))
        for b in self.buttons:
            b.draw(screen)
        for b in self.item_buttons:
            b.draw(screen)
        if self.status_msg:
            msg = self.font_small.render(self.status_msg, True, (200, 220, 255))
            screen.blit(msg, (40, 470))


class ShopScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.shop_path = "data/shop.json"
        self.inventory_path = "data/inventory.json"
        self.profile_path = "data/profile.json"
        self.data = load_json(self.shop_path, {"categories": []})
        self.inventory = load_json(self.inventory_path, {})
        self.profile = load_json(self.profile_path, {"coins": 1000})
        self.status_msg = ""
        self.buttons = [
            Button(pygame.Rect(40, 420, 160, 44), "Zurück", self.font_small, lambda: self.manager.set_scene("title"))
        ]
        self.item_buttons: list[Button] = []
        self._build_items()

    def on_enter(self) -> None:
        self.data = load_json(self.shop_path, {"categories": []})
        self.inventory = load_json(self.inventory_path, {})
        self.profile = load_json(self.profile_path, {"coins": 1000})
        self.status_msg = ""
        self._build_items()

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)
        for b in self.item_buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((14, 14, 24))
        title = self.font.render("Shop (Satire AE)", True, (240, 200, 120))
        screen.blit(title, (40, 30))
        coins_txt = self.font_small.render(f"Coins: {self.profile.get('coins',0)}", True, (180, 255, 200))
        screen.blit(coins_txt, (40, 70))
        y = 110
        for cat in self.data.get("categories", []):
            label = self.font_small.render(cat.get("name", "Kategorie"), True, (200, 220, 255))
            screen.blit(label, (40, y))
            y += 28
            for item in cat.get("items", []):
                y += 22
            y += 10
        for b in self.buttons:
            b.draw(screen)
        for b in self.item_buttons:
            b.draw(screen)
        if self.status_msg:
            msg = self.font_small.render(self.status_msg, True, (255, 220, 180))
            screen.blit(msg, (40, 470))

    # helpers
    def _build_items(self) -> None:
        self.item_buttons = []
        y = 110
        for cat in self.data.get("categories", []):
            y += 28  # category label space
            for item in cat.get("items", []):
                rect = pygame.Rect(320, y - 8, 260, 32)
                label = self._item_label(item)
                self.item_buttons.append(Button(rect, label, self.font_small, lambda it=item: self._buy(it)))
                y += 36
            y += 10

    def _item_label(self, item: dict) -> str:
        unlocked = self._is_unlocked(item)
        price = item.get("price", "?")
        name = item.get("name", "Item")
        return f"{name} ({'gekauft' if unlocked else price})"

    def _is_unlocked(self, item: dict) -> bool:
        item_id = item.get("id")
        for cat_items in self.inventory.values():
            for inv_item in cat_items if isinstance(cat_items, list) else []:
                if inv_item.get("id") == item_id:
                    return inv_item.get("unlocked", False)
        return False

    def _buy(self, item: dict) -> None:
        item_id = item.get("id")
        price = item.get("price", 0)
        if self._is_unlocked(item):
            self.status_msg = "Schon gekauft."
            return
        if self.profile.get("coins", 0) < price:
            self.status_msg = "Zu teuer."
            return
        self.profile["coins"] -= price
        # unlock in inventory data
        for cat, cat_items in self.inventory.items():
            if not isinstance(cat_items, list):
                continue
            for inv_item in cat_items:
                if inv_item.get("id") == item_id:
                    inv_item["unlocked"] = True
        save_json(self.profile_path, self.profile)
        save_json(self.inventory_path, self.inventory)
        self.status_msg = f"Gekauft: {item.get('name','')}"
        self._build_items()


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

    def _back(self) -> None:
        self.manager.set_scene(self.return_scene)

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

    def reset_game(self) -> None:
        self.game = None

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

    def _quit_to_title(self) -> None:
        if hasattr(self.play_scene, "reset_game"):
            self.play_scene.reset_game()
        self.manager.set_scene("title")

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        # draw underlying game frame
        if self.play_scene.game:
            self.play_scene.game.draw()
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        title = self.font.render("Paused", True, (255, 255, 255))
        screen.blit(title, (60, 120))
        for b in self.buttons:
            b.draw(screen)
