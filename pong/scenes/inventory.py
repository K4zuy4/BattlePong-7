from __future__ import annotations

import pygame
import logging
from pathlib import Path

from .base import Scene, SceneManager
from ..ui.api import button_column, ButtonSpec
from ..ui.widgets import ItemTile
from ..ui.layout import grid
from pong.core.input import Action

logger = logging.getLogger(__name__)


class InventoryScene(Scene):
    def __init__(self, manager: SceneManager, font, font_small, theme) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.theme = theme
        self.categories = []
        self.selected_cat_idx = 0
        self.selected_item_id: str | None = None
        self.items_grid: list[ItemTile] = []
        self.buttons: list = []
        self.status_msg = ""
        self._rebuild_from_ctx()

    def on_enter(self, payload: dict | None = None) -> None:
        self.status_msg = ""
        self._rebuild_from_ctx()
        logger.info("Inventory enter", extra={"categories": [c.get("id") for c in self.categories]})

    def _rebuild_from_ctx(self) -> None:
        inv = self.manager.app_ctx.get("inventory", {}) if hasattr(self.manager, "app_ctx") else {}
        cats = inv.get("categories", []) if isinstance(inv, dict) else []
        self.categories = cats if cats else []
        if self.selected_cat_idx >= len(self.categories):
            self.selected_cat_idx = 0
        self._build_buttons()
        self._build_items()

    def _build_buttons(self) -> None:
        self.buttons = []
        tab_w = 160
        tab_h = 44
        spacing = 10
        for i, c in enumerate(self.categories):
            rect = pygame.Rect(40 + i * (tab_w + spacing), 80, tab_w, tab_h)
            self.buttons.append(button_column(anchor=(rect.x, rect.y), width=tab_w, item_height=tab_h, spacing=0,
                                              specs=[ButtonSpec(c.get("label", c.get("id", "Cat")), action=lambda idx=i: self._set_category(idx))],
                                              font=self.font_small, theme=self.theme)[0])
        apply_rect = pygame.Rect(40, 420, 160, 44)
        back_rect = pygame.Rect(220, 420, 160, 44)
        self.buttons.append(button_column(anchor=(apply_rect.x, apply_rect.y), width=apply_rect.w, item_height=apply_rect.h,
                                          spacing=0, specs=[ButtonSpec("Apply", action=self._apply)],
                                          font=self.font_small, theme=self.theme)[0])
        self.buttons.append(button_column(anchor=(back_rect.x, back_rect.y), width=back_rect.w, item_height=back_rect.h,
                                          spacing=0, specs=[ButtonSpec("Back", action=self._back, variant="ghost")],
                                          font=self.font_small, theme=self.theme)[0])

    def _set_category(self, idx: int) -> None:
        self.selected_cat_idx = idx
        self.selected_item_id = None
        self.status_msg = ""
        self._build_items()

    def _build_items(self) -> None:
        self.items_grid = []
        if not self.categories:
            return
        cat = self.categories[self.selected_cat_idx]
        cat_id = cat.get("id")
        default_price = cat.get("default_price", 0)
        items = self._discover_items(cat_id, default_price)
        cols = 4
        cell_w = 120
        cell_h = 120
        spacing = (20, 32)
        positions = grid(anchor=(40, 150), cell=(cell_w, cell_h), cols=cols, spacing=spacing, count=len(items))
        for pos, item in zip(positions, items):
            rect = pygame.Rect(pos[0], pos[1], cell_w, cell_h)
            surf = None
            sprite = item.get("path")
            if sprite and Path(sprite).is_file():
                try:
                    raw = pygame.image.load(sprite).convert_alpha()
                    surf = pygame.transform.smoothscale(raw, (cell_w - 16, cell_h - 16))
                except Exception:
                    surf = None
            owned_set = self.manager.app_ctx.get("owned_items", {}).get(cat_id, set()) if hasattr(self.manager, "app_ctx") else set()
            locked = item.get("id") not in owned_set
            self.items_grid.append(
                ItemTile(
                    rect,
                    surf,
                    item.get("name", "Item"),
                    locked,
                    self._select_item_by_id,
                    item.get("id", ""),
                    price=item.get("price", default_price),
                    rarity=item.get("rarity", "common"),
                )
            )
        self.current_items = items
        if self.selected_item_id and self.selected_item_id not in {i.get("id") for i in items}:
            self.selected_item_id = None
        logger.info("Inventory items built", extra={"category": cat_id, "count": len(items)})

    def _discover_items(self, cat_id: str, default_price: int) -> list[dict]:
        # Prefer explicit items provided by inventory.json; fall back to folder discovery.
        items: list[dict] = []
        cat = next((c for c in self.categories if c.get("id") == cat_id), None)
        if cat:
            for itm in cat.get("items", []):
                path = itm.get("path")
                if not path:
                    continue
                items.append({
                    "id": itm.get("id", Path(path).stem),
                    "name": itm.get("name", Path(path).stem.replace("_", " ").title()),
                    "path": path,
                    "price": itm.get("price", default_price),
                    "rarity": itm.get("rarity", "common"),
                })
        if items:
            return items

        base = Path("skins") / cat_id
        if base.exists():
            for p in sorted(base.iterdir()):
                if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                    items.append({
                        "id": p.stem,
                        "name": p.stem.replace("_", " ").title(),
                        "path": str(p),
                        "price": default_price,
                        "rarity": "common",
                    })
        return items

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)
        for tile in self.items_grid:
            tile.handle_event(event)

    def handle_input(self, input_state) -> None:
        delta = input_state.nav_vertical()
        if delta != 0:
            # simple cycling over category buttons
            if self.buttons:
                idx = (self.selected_cat_idx + delta) % max(1, len(self.categories))
                self._set_category(idx)
        if hasattr(input_state, "consume") and input_state.consume(Action.CONFIRM):
            # activate first item in grid as a simple interaction
            if self.items_grid:
                first = self.items_grid[0]
                self._select_item_by_id(first.item_id)

    def update(self, dt: float) -> None:
        for b in self.buttons:
            b.update(dt)
        for tile in self.items_grid:
            tile.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((18, 18, 26))
        title = self.font.render("Inventory", True, (230, 230, 230))
        screen.blit(title, (40, 30))
        if self.categories:
            cat_label = self.categories[self.selected_cat_idx].get("label", "")
            cat_txt = self.font_small.render(cat_label, True, (200, 220, 240))
            screen.blit(cat_txt, (40, 110))
        for b in self.buttons:
            b.draw(screen)
        for tile in self.items_grid:
            tile.draw(screen, self.font_small, selected=tile.item_id == self.selected_item_id)
        if self.status_msg:
            msg = self.font_small.render(self.status_msg, True, (200, 220, 255))
            screen.blit(msg, (40, 470))

    def _select_item_by_id(self, item_id: str) -> None:
        if not self.categories:
            return
        cat_id = self.categories[self.selected_cat_idx].get("id")
        owned = self.manager.app_ctx.get("owned_items", {}).get(cat_id, set()) if hasattr(self.manager, "app_ctx") else set()
        item = next((i for i in self.current_items if i.get("id") == item_id), None)
        if not item:
            return
        price = item.get("price", 0)
        app = getattr(self.manager, "app", None)
        if not app:
            return
        if item_id not in owned:
            if app.credits < price:
                self.status_msg = f"Need {price - app.credits} more credits"
                return
            app.credits -= price
            app.owned_items.setdefault(cat_id, set()).add(item_id)
            app._save_wallet()
            app._save_owned_items()
            self.manager.app_ctx["credits"] = app.credits
            self.manager.app_ctx["owned_items"] = app.owned_items
            self.status_msg = f"Unlocked {item.get('name','')} for {price}C"
            logger.info("Inventory purchase", extra={"category": cat_id, "item": item_id, "price": price, "credits_after": app.credits})
        else:
            self.status_msg = f"Selected {item.get('name','')}"
        self.selected_item_id = item_id
        # refresh grid to clear lock overlay
        self._build_items()

    def _apply(self) -> None:
        # For now, apply means set ball/paddle skin if present
        if not self.categories:
            return
        cat_id = self.categories[self.selected_cat_idx].get("id")
        if not self.current_items:
            return
        item = next((i for i in self.current_items if i.get("id") == self.selected_item_id), None)
        if not item:
            item = self.current_items[0]
        app = getattr(self.manager, "app", None)
        if not app:
            return
        owned = app.owned_items.get(cat_id, set())
        if item.get("id") not in owned:
            self.status_msg = "Unlock first"
            return
        if cat_id == "ball":
            try:
                idx = app.ball_skins.index(item.get("path"))
            except ValueError:
                idx = 0
            app._apply_ball_skin(idx)
            self.status_msg = f"Applied {item.get('name','')}"
        elif cat_id == "paddle":
            try:
                idx = app.paddle_skins.index(item.get("path"))
            except ValueError:
                idx = 0
            app._apply_paddle_skin(idx)
            self.status_msg = f"Applied {item.get('name','')}"

    def _back(self) -> None:
        if self.manager.previous_name:
            self.manager.pop()
        else:
            self.manager.set_scene("title")
