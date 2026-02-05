from __future__ import annotations

from pathlib import Path
import sys
import logging

import pygame

# Allow running as script
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    __package__ = "pong.scenes"

from ..data_io import load_json, save_json
from ..events import SettingsChangeRequested
from .base import Scene, SceneManager
from ..ui.widgets import Button, ItemTile

logger = logging.getLogger(__name__)


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
        self.item_tiles: list[ItemTile] = []
        self.status_msg = ""
        self._build_buttons()

    def on_enter(self) -> None:
        self.data = load_json(self.inventory_path, {})
        self._prune_missing_assets()
        self.loadout = load_json(self.loadout_path, {})
        self._scan_and_merge_skins()
        self.categories = list(self.data.keys()) or ["paddle", "ball", "background", "trail", "animation"]
        self.current_cat_idx = 0
        self.status_msg = ""
        self._build_buttons()
        logger.info("Inventory opened")

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
        self.item_tiles = []
        items = self.data.get(self.categories[self.current_cat_idx], [])
        cols = 8
        tile_size = 90
        padding = 18
        start_x = 40
        start_y = 150
        for idx, item in enumerate(items[:12]):
            row = idx // cols
            col = idx % cols
            x = start_x + col * (tile_size + padding)
            y = start_y + row * (tile_size + 2 * padding)
            rect = pygame.Rect(x, y, tile_size, tile_size)
            surf = None
            sprite_path = item.get("sprite")
            if sprite_path and Path(sprite_path).is_file():
                try:
                    raw = pygame.image.load(sprite_path).convert_alpha()
                    surf = pygame.transform.smoothscale(raw, (tile_size - 12, tile_size - 12))
                except Exception:
                    surf = None
            label = item.get("name", "Item")
            locked = not item.get("unlocked", False)
            self.item_tiles.append(
                ItemTile(rect, surf, label, locked, self._select_item_by_id, item.get("id", ""))
            )

    def _scan_and_merge_skins(self) -> None:
        exts = {".png", ".jpg", ".jpeg"}
        base = Path("skins")
        folders = {
            "paddle": base / "paddle",
            "ball": base / "ball",
            "background": base / "background",
        }
        for cat, folder in folders.items():
            if not folder.exists():
                continue
            existing = self.data.setdefault(cat, [])
            for file in folder.iterdir():
                if not file.is_file() or file.suffix.lower() not in exts:
                    continue
                item_id = f"{cat}_{file.stem}"
                if any(i.get("id") == item_id for i in existing):
                    continue
                name = file.stem.replace("_", " ").title()
                existing.append(
                    {
                        "id": item_id,
                        "name": name,
                        "sprite": file.as_posix(),
                        "unlocked": False,
                        "price": 400,
                    }
                )
        save_json(self.inventory_path, self.data)

    def _prune_missing_assets(self) -> None:
        changed = False
        for cat, items in list(self.data.items()):
            if not isinstance(items, list):
                continue
            pruned = []
            for item in items:
                sprite = item.get("sprite")
                if sprite and not Path(sprite).is_file():
                    changed = True
                    continue
                pruned.append(item)
            self.data[cat] = pruned
        if changed:
            save_json(self.inventory_path, self.data)

    def _select_item_by_id(self, item_id: str) -> None:
        cat = self.categories[self.current_cat_idx]
        items = self.data.get(cat, [])
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return
        if not item.get("unlocked", False):
            self.status_msg = "Locked. Kauf im Shop."
            return
        self.loadout[cat] = item_id
        self.app_ctx.setdefault("selected_items", {})[cat] = item
        self.status_msg = f"Ausgewählt: {item.get('name','')}"
        logger.debug("Inventory select", extra={"category": cat, "item": item_id})

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
        if "trail" in self.loadout:
            self.bus.publish(
                SettingsChangeRequested(section="trail", values={"effect": self.loadout.get("trail", "trail_none")})
            )
        if sprites:
            self.bus.publish(SettingsChangeRequested(section="sprites", values=sprites))
        self.manager.set_scene("title")
        logger.info("Inventory applied", extra={"loadout": self.loadout})

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)
        for tile in self.item_tiles:
            tile.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((18, 18, 26))
        title = self.font.render("Inventory", True, (230, 230, 230))
        screen.blit(title, (40, 30))
        for b in self.buttons:
            b.draw(screen)
        current_cat = self.categories[self.current_cat_idx]
        selected_id = self.loadout.get(current_cat)
        for tile in self.item_tiles:
            tile.draw(screen, self.font_small, selected=(tile.item_id == selected_id))
        if self.status_msg:
            msg = self.font_small.render(self.status_msg, True, (200, 220, 255))
            screen.blit(msg, (40, 470))
