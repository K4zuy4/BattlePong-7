from __future__ import annotations

import random
from pathlib import Path
import sys
import logging
import pygame

# Allow running as script (no package context)
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    __package__ = "pong.scenes"

from ..data_io import load_json, save_json
from .base import Scene, SceneManager
from ..ui.widgets import Button

logger = logging.getLogger(__name__)

class MiniMatch:
    """Lightweight auto-play pong preview for backgrounds."""

    def __init__(self, size: tuple[int, int]) -> None:
        self.width, self.height = size
        self.reset()

    def reset(self) -> None:
        self.ball_pos = [self.width / 2, self.height / 2]
        angle = random.choice([-0.6, -0.4, 0.4, 0.6])
        speed = 180
        self.ball_vel = [speed if random.random() > 0.5 else -speed, speed * angle]
        self.ball_radius = 8
        self.paddle_h = 50
        self.paddle_w = 8
        self.paddle_speed = 220
        self.left_y = (self.height - self.paddle_h) / 2
        self.right_y = (self.height - self.paddle_h) / 2

    def update(self, dt: float) -> None:
        bx, by = self.ball_pos
        vx, vy = self.ball_vel

        def chase(py):
            center = py + self.paddle_h / 2
            return -1 if center > by else (1 if center < by else 0)

        self.left_y += chase(self.left_y) * self.paddle_speed * dt
        self.right_y += chase(self.right_y) * self.paddle_speed * dt
        self.left_y = max(0, min(self.height - self.paddle_h, self.left_y))
        self.right_y = max(0, min(self.height - self.paddle_h, self.right_y))

        bx += vx * dt
        by += vy * dt

        if by - self.ball_radius < 0 and vy < 0:
            by = self.ball_radius
            vy *= -1
        elif by + self.ball_radius > self.height and vy > 0:
            by = self.height - self.ball_radius
            vy *= -1

        if bx - self.ball_radius <= self.paddle_w:
            if self.left_y <= by <= self.left_y + self.paddle_h:
                bx = self.paddle_w + self.ball_radius
                vx *= -1
        if bx + self.ball_radius >= self.width - self.paddle_w:
            if self.right_y <= by <= self.right_y + self.paddle_h:
                bx = self.width - self.paddle_w - self.ball_radius
                vx *= -1

        if bx < -20 or bx > self.width + 20:
            self.reset()
            return

        self.ball_pos = [bx, by]
        self.ball_vel = [vx, vy]

    def draw(self, surf: pygame.Surface, bg: pygame.Surface | None) -> None:
        if bg:
            surf.blit(bg, (0, 0))
        else:
            surf.fill((12, 16, 26))
        pygame.draw.line(surf, (80, 90, 110), (self.width // 2, 0), (self.width // 2, self.height), 1)
        pygame.draw.rect(
            surf, (230, 230, 240), pygame.Rect(0, int(self.left_y), self.paddle_w, self.paddle_h), border_radius=2
        )
        pygame.draw.rect(
            surf,
            (230, 230, 240),
            pygame.Rect(self.width - self.paddle_w, int(self.right_y), self.paddle_w, self.paddle_h),
            border_radius=2,
        )
        pygame.draw.circle(surf, (255, 220, 150), (int(self.ball_pos[0]), int(self.ball_pos[1])), self.ball_radius)


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
            Button(pygame.Rect(40, 420, 160, 44), "Zurück", self.font_small, lambda: self.manager.set_scene("title")),
            Button(pygame.Rect(220, 420, 220, 44), "Gratis +500 Coins", self.font_small, self._add_coins),
        ]
        self.buy_button = Button(
            pygame.Rect(500, 190, 160, 44), "Kaufen", self.font_small, self._buy_current
        )
        self.entries: list[dict] = []
        screen_w = pygame.display.get_surface().get_width()
        self.preview_rect = pygame.Rect(40, 110, 420, 240)
        self.arrow_left = pygame.Rect(self.preview_rect.left - 34, self.preview_rect.top, 28, self.preview_rect.height)
        self.arrow_right = pygame.Rect(self.preview_rect.right + 6, self.preview_rect.top, 28, self.preview_rect.height)
        self.view_rect = self.preview_rect.copy()
        self.scroll_offset = 0
        self.max_content_height = 0
        self.confirm_open = False
        self.pending_item: dict | None = None
        self.confirm_buttons: list[Button] = []
        self.bg_items: list[dict] = []
        self.bg_index = 0
        self.preview_match = MiniMatch((self.preview_rect.width, self.preview_rect.height))
        self.preview_bg_surface: pygame.Surface | None = None
        self.ball_items: list[dict] = []
        self.ball_index = 0
        self.ball_angle = 0.0
        self.trail_items: list[dict] = []
        self.trail_index = 0
        self.trail_pos = pygame.Vector2(self.preview_rect.width / 3, self.preview_rect.height / 2)
        self.trail_vel = pygame.Vector2(160, 90)
        self.trail_points: list[pygame.Vector2] = []
        self.selected_category: str | None = None
        self.tab_buttons: list[dict] = []
        self._build_tabs()
        self._build_items()
        logger.info("Shop initialized")

    def on_enter(self) -> None:
        self.data = load_json(self.shop_path, {"categories": []})
        self.inventory = load_json(self.inventory_path, {})
        self._prune_inventory()
        self._prune_shop_catalog()
        self.profile = load_json(self.profile_path, {"coins": 1000})
        self.status_msg = ""
        self._ensure_catalog_from_inventory()
        self._collect_backgrounds()
        self._collect_balls()
        self._collect_trails()
        self._set_preview_bg(0)
        if self.data.get("categories"):
            self.selected_category = self.data["categories"][0].get("name")
        self._build_tabs()
        self._build_items()
        logger.info("Shop entered", extra={"categories": [c.get('name') for c in self.data.get('categories', [])]})

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.confirm_open:
            for b in self.confirm_buttons:
                b.handle_event(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab in self.tab_buttons:
                if tab["rect"].collidepoint(event.pos):
                    self.selected_category = tab["name"]
                    if "Background" in self.selected_category:
                        self._set_preview_bg(self.bg_index if self.bg_items else 0)
                    elif "Ball" in self.selected_category:
                        self.ball_index = 0
                    elif "Trail" in self.selected_category:
                        self.trail_index = 0
                    self._build_items()
                    return

        for b in self.buttons:
            b.handle_event(event)
        self.buy_button.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.arrow_left.collidepoint(pos):
                self._handle_arrow(-1)
                return
            if self.arrow_right.collidepoint(pos):
                self._handle_arrow(1)
                return
            # buy current item via dedicated button
        logger.debug("Shop handle_event", extra={"event": event.type})

    def update(self, dt: float) -> None:
        self.preview_match.update(dt)
        self.ball_angle = (self.ball_angle + 90 * dt) % 360
        self._update_trail(dt)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((14, 14, 24))
        title = self.font.render("Shop (Satire AE)", True, (240, 200, 120))
        screen.blit(title, (40, 30))
        coins_txt = self.font_small.render(f"Coins: {self.profile.get('coins',0)}", True, (180, 255, 200))
        screen.blit(coins_txt, (40, 70))
        self._draw_tabs(screen)
        self._draw_preview(screen)
        for b in self.buttons:
            b.draw(screen)
        self.buy_button.draw(screen)
        # Hinweis unten nur für Statusmeldungen, nicht für bereits gekauft
        if self.status_msg:
            msg = self.font_small.render(self.status_msg, True, (255, 220, 180))
            screen.blit(msg, (40, 470))
        if self.confirm_open and self.pending_item:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            box = pygame.Rect(screen.get_width() // 2 - 200, screen.get_height() // 2 - 90, 400, 180)
            pygame.draw.rect(screen, (30, 40, 60), box, border_radius=12)
            pygame.draw.rect(screen, (255, 255, 255), box, 2, border_radius=12)
            msg = f"Kaufen {self.pending_item.get('name','Item')} für {self.pending_item.get('price','?')}?"
            txt = self.font.render("Bestätigen", True, (230, 230, 230))
            screen.blit(txt, (box.x + 20, box.y + 16))
            msg_surf = self.font_small.render(msg, True, (220, 220, 220))
            screen.blit(msg_surf, (box.x + 20, box.y + 64))
            for b in self.confirm_buttons:
                b.draw(screen)

    # helpers
    def _build_items(self) -> None:
        # no scroll list needed anymore
        self.entries = []
        self.max_content_height = 0

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
        self.confirm_open = False
        self.pending_item = None
        self._collect_backgrounds()
        logger.info("Item bought", extra={"item": item_id, "coins": self.profile.get("coins", 0)})
        # keep selection consistent
        self._sync_selection_after_buy()

    def _add_coins(self) -> None:
        self.profile["coins"] = self.profile.get("coins", 0) + 500
        save_json(self.profile_path, self.profile)
        self.status_msg = "+500 Coins hinzugefügt (gratis)"
        logger.info("Coins granted", extra={"coins": self.profile.get("coins", 0)})

    def _ensure_catalog_from_inventory(self) -> None:
        def add_item(cat_name: str, inv_item: dict) -> None:
            cat_list = None
            for cat in self.data.setdefault("categories", []):
                if cat.get("name") == cat_name:
                    cat_list = cat
                    break
            if cat_list is None:
                cat_list = {"name": cat_name, "items": []}
                self.data["categories"].append(cat_list)
            if any(i.get("id") == inv_item.get("id") for i in cat_list["items"]):
                return
            cat_list["items"].append(
                {
                    "id": inv_item.get("id"),
                    "name": inv_item.get("name", "Item"),
                    "price": inv_item.get("price", 400),
                    "icon": inv_item.get("sprite"),
                }
            )

        for cat_name, inv_items in self.inventory.items():
            if not isinstance(inv_items, list):
                continue
            for inv_item in inv_items:
                if inv_item.get("unlocked", False):
                    continue
                add_item(cat_name.title(), inv_item)
        save_json(self.shop_path, self.data)
        logger.debug("Shop catalog synced", extra={"categories": len(self.data.get('categories', []))})

    def _prune_shop_catalog(self) -> None:
        changed = False
        pruned_categories = []
        for cat in self.data.get("categories", []):
            if not isinstance(cat.get("items"), list):
                continue
            new_items = []
            for item in cat["items"]:
                icon = item.get("icon")
                if icon and not Path(icon).is_file():
                    changed = True
                    continue
                new_items.append(item)
            if new_items:
                cat["items"] = new_items
                pruned_categories.append(cat)
            else:
                changed = True
        self.data["categories"] = pruned_categories
        if changed:
            save_json(self.shop_path, self.data)
            logger.debug("Shop catalog pruned for missing icons")

    def _prune_inventory(self) -> None:
        changed = False
        for cat, items in list(self.inventory.items()):
            if not isinstance(items, list):
                continue
            filtered = []
            for item in items:
                sprite = item.get("sprite")
                if sprite and not Path(sprite).is_file():
                    changed = True
                    continue
                filtered.append(item)
            self.inventory[cat] = filtered
        if changed:
            save_json(self.inventory_path, self.inventory)
            logger.debug("Inventory pruned for missing assets")

    def _collect_backgrounds(self) -> None:
        self.bg_items = []
        for item in self.inventory.get("background", []):
            sprite = item.get("sprite")
            if sprite and Path(sprite).is_file():
                self.bg_items.append(item)
        if not self.bg_items:
            self.preview_bg_surface = None
            return
        self.bg_index %= len(self.bg_items)
        self._set_preview_bg(self.bg_index)

    def _collect_balls(self) -> None:
        self.ball_items = []
        for item in self.inventory.get("ball", []):
            sprite = item.get("sprite")
            if sprite and Path(sprite).is_file():
                self.ball_items.append(item)
        self.ball_index %= len(self.ball_items or [1])

    def _collect_trails(self) -> None:
        self.trail_items = []
        for item in self.inventory.get("trail", []):
            self.trail_items.append(item)
        self.trail_index %= len(self.trail_items or [1])

    def _set_preview_bg(self, idx: int) -> None:
        if not self.bg_items:
            self.preview_bg_surface = None
            return
        item = self.bg_items[idx % len(self.bg_items)]
        sprite = item.get("sprite")
        if sprite and Path(sprite).is_file():
            try:
                raw = pygame.image.load(sprite).convert()
                self.preview_bg_surface = pygame.transform.smoothscale(raw, self.preview_rect.size)
            except Exception:
                self.preview_bg_surface = None
        else:
            self.preview_bg_surface = None

    def _cycle_bg(self, direction: int) -> None:
        if not self.bg_items:
            return
        self.bg_index = (self.bg_index + direction) % len(self.bg_items)
        self._set_preview_bg(self.bg_index)

    def _cycle_ball(self, direction: int) -> None:
        if not self.ball_items:
            return
        self.ball_index = (self.ball_index + direction) % len(self.ball_items)

    def _cycle_trail(self, direction: int) -> None:
        if not self.trail_items:
            return
        self.trail_index = (self.trail_index + direction) % len(self.trail_items)

    def _open_confirm(self, item: dict) -> None:
        self.pending_item = item
        self.confirm_open = True
        box = pygame.Rect(
            self.view_rect.centerx - 200,
            self.view_rect.top - 120,
            400,
            120,
        )
        y_btn = box.bottom + 12
        self.confirm_buttons = [
            Button(pygame.Rect(box.x, y_btn, 120, 38), "Kaufen", self.font_small, lambda: self._buy(item)),
            Button(pygame.Rect(box.x + 160, y_btn, 120, 38), "Abbrechen", self.font_small, self._cancel_confirm),
        ]

    def _cancel_confirm(self) -> None:
        self.confirm_open = False
        self.pending_item = None

    def _scroll(self, delta: int) -> None:
        max_off = max(0, self.max_content_height - self.view_rect.height)
        self.scroll_offset = max(0, min(self.scroll_offset + delta, max_off))

    # preview helpers
    def _build_tabs(self) -> None:
        self.tab_buttons = []
        x = 200
        y = 70
        padding = 12
        for cat in self.data.get("categories", []):
            name = cat.get("name", "Kategorie")
            txt = self.font_small.render(name, True, (255, 255, 255))
            w = txt.get_width() + 24
            rect = pygame.Rect(x, y, w, 30)
            self.tab_buttons.append({"name": name, "rect": rect})
            x += w + padding

    def _draw_tabs(self, screen: pygame.Surface) -> None:
        for tab in self.tab_buttons:
            rect = tab["rect"]
            active = tab["name"] == self.selected_category
            color = (100, 130, 170) if active else (70, 90, 120)
            pygame.draw.rect(screen, color, rect, border_radius=6)
            pygame.draw.rect(screen, (255, 255, 255), rect, 1, border_radius=6)
            txt = self.font_small.render(tab["name"], True, (255, 255, 255))
            txt_rect = txt.get_rect(center=rect.center)
            screen.blit(txt, txt_rect)

    def _draw_preview(self, screen: pygame.Surface) -> None:
        cat = (self.selected_category or "").lower()
        if "background" in cat:
            surf = pygame.Surface(self.preview_rect.size).convert()
            self.preview_match.draw(surf, self.preview_bg_surface)
            screen.blit(surf, self.preview_rect.topleft)
        elif "ball" in cat:
            surf = pygame.Surface(self.preview_rect.size, pygame.SRCALPHA)
            surf.fill((10, 12, 20))
            if self.ball_items:
                item = self.ball_items[self.ball_index]
                sprite = item.get("sprite")
                size = min(self.preview_rect.width, self.preview_rect.height) - 40
                if sprite and Path(sprite).is_file():
                    try:
                        raw = pygame.image.load(sprite).convert_alpha()
                        img = pygame.transform.smoothscale(raw, (size, size))
                        img = pygame.transform.rotate(img, self.ball_angle)
                        img_rect = img.get_rect(center=(self.preview_rect.width // 2, self.preview_rect.height // 2))
                        surf.blit(img, img_rect.topleft)
                    except Exception:
                        pass
                pygame.draw.circle(
                    surf,
                    (255, 230, 160),
                    (self.preview_rect.width // 2, self.preview_rect.height // 2),
                    size // 2,
                    width=2,
                )
                label = self.font_small.render(item.get("name", ""), True, (230, 230, 230))
                surf.blit(label, (10, 10))
            screen.blit(surf, self.preview_rect.topleft)
        elif "trail" in cat:
            surf = pygame.Surface(self.preview_rect.size, pygame.SRCALPHA)
            surf.fill((12, 16, 24))
            self._draw_trail_preview(surf)
            if self.trail_items:
                label = self.font_small.render(self.trail_items[self.trail_index].get("name", ""), True, (230, 230, 230))
                surf.blit(label, (10, 10))
            screen.blit(surf, self.preview_rect.topleft)
        else:
            pygame.draw.rect(screen, (20, 24, 34), self.preview_rect)

        pygame.draw.rect(screen, (80, 100, 140), self.arrow_left, border_radius=6)
        pygame.draw.polygon(
            screen,
            (255, 255, 255),
            [
                (self.arrow_left.centerx + 6, self.arrow_left.centery - 12),
                (self.arrow_left.centerx - 6, self.arrow_left.centery),
                (self.arrow_left.centerx + 6, self.arrow_left.centery + 12),
            ],
        )
        pygame.draw.rect(screen, (80, 100, 140), self.arrow_right, border_radius=6)
        pygame.draw.polygon(
            screen,
            (255, 255, 255),
            [
                (self.arrow_right.centerx - 6, self.arrow_right.centery - 12),
                (self.arrow_right.centerx + 6, self.arrow_right.centery),
                (self.arrow_right.centerx - 6, self.arrow_right.centery + 12),
            ],
        )
        # update buy button label based on current item unlocked state
        current = self._current_item()
        if current and self._is_unlocked(current):
            self.buy_button.label = "Gekauft"
        else:
            self.buy_button.label = "Kaufen"

    def _handle_arrow(self, direction: int) -> None:
        cat = (self.selected_category or "").lower()
        if "background" in cat:
            self._cycle_bg(direction)
        elif "ball" in cat:
            self._cycle_ball(direction)
        elif "trail" in cat:
            self._cycle_trail(direction)

    def _update_trail(self, dt: float) -> None:
        bounds = pygame.Rect(0, 0, self.preview_rect.width, self.preview_rect.height)
        self.trail_pos += self.trail_vel * dt
        if self.trail_pos.x < 10 or self.trail_pos.x > bounds.width - 10:
            self.trail_vel.x *= -1
        if self.trail_pos.y < 10 or self.trail_pos.y > bounds.height - 10:
            self.trail_vel.y *= -1
        self.trail_points.insert(0, self.trail_pos.copy())
        if len(self.trail_points) > 10:
            self.trail_points.pop()

    def _trail_preview_color(self) -> tuple[int, int, int]:
        item = self._current_item()
        trail_id = item.get("id") if item else "trail_none"
        match trail_id:
            case "trail_fire":
                return (255, 120, 60)
            case "trail_neon":
                return (120, 200, 255)
            case "trail_spark":
                return (255, 230, 140)
            case "trail_pixel":
                return (180, 180, 255)
            case "trail_rainbow":
                return (255, 80, 200)
            case "trail_smoke":
                return (180, 180, 180)
            case _:
                return (200, 200, 200)

    def _draw_trail_preview(self, surf: pygame.Surface) -> None:
        effect = (self._current_item() or {}).get("id", "trail_none")
        color = self._trail_preview_color()
        for i, p in enumerate(self.trail_points):
            alpha = max(0, 255 - i * 22)
            size = 8
            if effect == "trail_fire":
                col = (255, 140 - i * 4, 60, alpha)
                pygame.draw.circle(surf, col, (int(p.x), int(p.y)), size)
            elif effect == "trail_neon":
                pygame.draw.circle(surf, (color[0], color[1], color[2], alpha), (int(p.x), int(p.y)), size)
                pygame.draw.circle(surf, (255, 255, 255, alpha), (int(p.x), int(p.y)), max(1, size // 2))
            elif effect == "trail_spark":
                col = (255, 230, 160, alpha)
                pygame.draw.line(surf, col, (p.x - 8, p.y), (p.x + 8, p.y), width=2)
                pygame.draw.line(surf, col, (p.x, p.y - 8), (p.x, p.y + 8), width=2)
            elif effect == "trail_pixel":
                pygame.draw.rect(surf, (*color, alpha), pygame.Rect(p.x - 5, p.y - 5, 10, 10))
            elif effect == "trail_rainbow":
                col = self._trail_preview_color()
                pygame.draw.circle(surf, (*col, alpha), (int(p.x), int(p.y)), size)
            elif effect == "trail_smoke":
                pygame.draw.circle(surf, (160, 160, 160, alpha), (int(p.x), int(p.y)), size)
            else:
                pygame.draw.circle(surf, (*color, alpha), (int(p.x), int(p.y)), size)
        pygame.draw.circle(
            surf,
            (255, 230, 160),
            (int(self.trail_pos.x), int(self.trail_pos.y)),
            10,
        )

    def _current_item(self) -> dict | None:
        cat = (self.selected_category or "").lower()
        if "background" in cat and self.bg_items:
            return self.bg_items[self.bg_index]
        if "ball" in cat and self.ball_items:
            return self.ball_items[self.ball_index]
        if "trail" in cat and self.trail_items:
            return self.trail_items[self.trail_index]
        return None

    def _buy_current(self) -> None:
        item = self._current_item()
        if not item:
            self.status_msg = "Kein Item ausgewählt."
            return
        self._open_confirm(item)

    def _sync_selection_after_buy(self) -> None:
        # ensure indices stay in range after unlocking
        if self.bg_items:
            self.bg_index %= len(self.bg_items)
        if self.ball_items:
            self.ball_index %= len(self.ball_items)
        if self.trail_items:
            self.trail_index %= len(self.trail_items)
