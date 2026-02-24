"""Small internal UI builder helpers for scenes.

Focus: fast creation of button columns/rows wired to scene navigation or
custom callbacks. Keeps layout math and styling in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
import pygame

from .widgets import Button, DEFAULT_THEME


@dataclass
class ButtonSpec:
    label: str
    action: Callable[[], None] | None = None
    route: str | None = None
    variant: str = "primary"


def button_column(
    *,
    anchor: tuple[int, int],
    width: int,
    item_height: int,
    spacing: int,
    specs: Sequence[ButtonSpec],
    font: pygame.font.Font,
    theme=DEFAULT_THEME,
    on_route: Callable[[str], None] | None = None,
) -> list[Button]:
    """Create a vertical stack of buttons from specs.

    - anchor: top-left position of the first button
    - width / item_height: geometry for each button
    - spacing: vertical spacing in pixels
    - on_route: optional router; if provided and spec.action is None, we call on_route(spec.route)
    """

    buttons: list[Button] = []
    x, y = anchor
    for i, spec in enumerate(specs):
        rect = pygame.Rect(x, y + i * (item_height + spacing), width, item_height)
        if spec.action:
            action = spec.action
        elif on_route and spec.route:
            action = lambda r=spec.route: on_route(r)
        else:
            action = lambda: None
        buttons.append(Button(rect, spec.label, font, action, variant=spec.variant, theme=theme))
    return buttons


def button_row(
    *,
    anchor: tuple[int, int],
    item_width: int,
    item_height: int,
    spacing: int,
    specs: Sequence[ButtonSpec],
    font: pygame.font.Font,
    theme=DEFAULT_THEME,
    on_route: Callable[[str], None] | None = None,
) -> list[Button]:
    """Horizontal helper for quick layouts."""
    buttons: list[Button] = []
    x, y = anchor
    for i, spec in enumerate(specs):
        rect = pygame.Rect(x + i * (item_width + spacing), y, item_width, item_height)
        if spec.action:
            action = spec.action
        elif on_route and spec.route:
            action = lambda r=spec.route: on_route(r)
        else:
            action = lambda: None
        buttons.append(Button(rect, spec.label, font, action, variant=spec.variant, theme=theme))
    return buttons
