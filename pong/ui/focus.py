from __future__ import annotations

"""Simple focus manager for directional navigation."""

from dataclasses import dataclass
from typing import List, Callable
import pygame


@dataclass
class FocusItem:
    rect: pygame.Rect
    on_focus: Callable[[], None] | None = None
    on_activate: Callable[[], None] | None = None


class FocusManager:
    def __init__(self) -> None:
        self.items: List[FocusItem] = []
        self.index: int = 0

    def set_items(self, items: List[FocusItem]) -> None:
        self.items = items
        self.index = 0 if items else -1
        self._call_focus()

    def move(self, delta: int) -> None:
        if not self.items:
            return
        self.index = (self.index + delta) % len(self.items)
        self._call_focus()

    def activate(self) -> None:
        if self.index < 0 or self.index >= len(self.items):
            return
        item = self.items[self.index]
        if item.on_activate:
            item.on_activate()

    def current_rect(self) -> pygame.Rect | None:
        if self.index < 0 or self.index >= len(self.items):
            return None
        return self.items[self.index].rect

    def _call_focus(self) -> None:
        if self.index < 0 or self.index >= len(self.items):
            return
        item = self.items[self.index]
        if item.on_focus:
            item.on_focus()
