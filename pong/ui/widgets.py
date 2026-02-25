"""Minimal UI widgets plus a small styling/animation API."""

from __future__ import annotations

import pygame
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# --- Theme & helpers ------------------------------------------------------ #

@dataclass(frozen=True)
class ButtonStyle:
    base: tuple[int, int, int]
    hover: tuple[int, int, int]
    press: tuple[int, int, int]
    border: tuple[int, int, int]
    text: tuple[int, int, int]
    radius: int = 10


@dataclass
class ThemeTokens:
    variants: dict[str, ButtonStyle]

    def resolve(self, variant: str) -> ButtonStyle:
        return self.variants.get(variant, self.variants["primary"])


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def _lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (int(_lerp(c1[0], c2[0], t)), int(_lerp(c1[1], c2[1], t)), int(_lerp(c1[2], c2[2], t)))


DEFAULT_THEME = ThemeTokens(
    variants={
        "primary": ButtonStyle(
            base=(28, 32, 44),
            hover=(74, 110, 188),
            press=(20, 22, 30),
            border=(240, 240, 255),
            text=(250, 250, 255),
            radius=12,
        ),
        "ghost": ButtonStyle(
            base=(16, 18, 24),
            hover=(44, 54, 76),
            press=(10, 12, 16),
            border=(170, 190, 220),
            text=(220, 230, 245),
            radius=12,
        ),
    }
)


# --- Widgets -------------------------------------------------------------- #

class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        on_click,
        variant: str = "primary",
        theme: ThemeTokens = DEFAULT_THEME,
    ) -> None:
        self.rect = rect
        self.label = label
        self.font = font
        self.on_click = on_click
        self.hovered = False
        self.pressed = False
        self.variant = variant
        self.theme = theme
        self._hover_t = 0.0
        self._press_t = 0.0
        self.focused = False

    # Interaction --------------------------------------------------------- #
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.on_click()
                logger.debug("Button click", extra={"label": self.label})
            self.pressed = False

    def update(self, dt: float) -> None:
        target_hover = 1.0 if self.hovered else 0.0
        target_press = 1.0 if self.pressed else 0.0
        speed = 8.0
        self._hover_t += (target_hover - self._hover_t) * min(1.0, dt * speed)
        self._press_t += (target_press - self._press_t) * min(1.0, dt * speed)

    # Drawing ------------------------------------------------------------- #
    def draw(self, screen: pygame.Surface) -> None:
        style = self.theme.resolve(self.variant)
        # Blend between hover/press/base
        col_hover = _lerp_color(style.base, style.hover, self._hover_t)
        col_press = _lerp_color(col_hover, style.press, self._press_t)
        pygame.draw.rect(screen, col_press, self.rect, border_radius=style.radius)
        border_w = 4 if self.focused else 2
        pygame.draw.rect(screen, style.border, self.rect, width=border_w, border_radius=style.radius)
        text = self.font.render(self.label, True, style.text)
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)
        logger.debug("Button draw", extra={"label": self.label, "hover": self._hover_t, "press": self._press_t})

    def set_focus(self, focused: bool) -> None:
        self.focused = focused


class ItemTile:
    def __init__(
        self,
        rect: pygame.Rect,
        image: pygame.Surface | None,
        label: str,
        locked: bool,
        on_click,
        item_id: str,
    ) -> None:
        self.rect = rect
        self.image = image
        self.label = label
        self.locked = locked
        self.on_click = on_click
        self.hovered = False
        self.item_id = item_id

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and not self.locked:
                self.on_click(self.item_id)

    def update(self, dt: float) -> None:
        # Placeholder for future hover/press animations
        _ = dt

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, selected: bool = False) -> None:
        base = (50, 60, 80)
        hover = (80, 100, 130)
        locked_col = (90, 60, 60)
        color = locked_col if self.locked else (hover if self.hovered else base)
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, width=2 if not selected else 4, border_radius=8)
        if self.image:
            img_rect = self.image.get_rect(center=self.rect.center)
            screen.blit(self.image, img_rect.topleft)
        label_surf = font.render(self.label, True, (230, 230, 230))
        label_rect = label_surf.get_rect(center=(self.rect.centerx, self.rect.bottom + 12))
        screen.blit(label_surf, label_rect)
        if self.locked:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, self.rect.topleft)
            lock_txt = font.render("Locked", True, (255, 180, 180))
            lock_rect = lock_txt.get_rect(center=self.rect.center)
            screen.blit(lock_txt, lock_rect)
        logger.debug("ItemTile draw", extra={"id": self.item_id, "locked": self.locked, "selected": selected})

class Label:
    def __init__(self, text: str, pos: tuple[int, int], font: pygame.font.Font, color=(230, 230, 230)) -> None:
        self.text = text
        self.pos = pos
        self.font = font
        self.color = color

    def draw(self, screen: pygame.Surface) -> None:
        img = self.font.render(self.text, True, self.color)
        screen.blit(img, self.pos)
        logger.debug("Label draw", extra={"text": self.text})


class Toggle:
    def __init__(self, rect: pygame.Rect, value: bool, on_change, label: str | None, font: pygame.font.Font) -> None:
        self.rect = rect
        self.value = value
        self.on_change = on_change
        self.label = label
        self.font = font
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                self.on_change(self.value)

    def update(self, dt: float) -> None:
        _ = dt

    def draw(self, screen: pygame.Surface) -> None:
        base = (60, 70, 90)
        on_col = (90, 180, 120)
        color = on_col if self.value else base
        pygame.draw.rect(screen, color, self.rect, border_radius=self.rect.height // 2)
        knob_size = self.rect.height - 6
        knob_x = self.rect.left + 3 if not self.value else self.rect.right - knob_size - 3
        knob_rect = pygame.Rect(knob_x, self.rect.top + 3, knob_size, knob_size)
        pygame.draw.ellipse(screen, (240, 240, 255), knob_rect)
        if self.label:
            text = self.font.render(self.label, True, (220, 230, 240))
            screen.blit(text, (self.rect.right + 12, self.rect.centery - text.get_height() // 2))


class Slider:
    def __init__(
        self,
        rect: pygame.Rect,
        value: float,
        on_change,
        font: pygame.font.Font | None = None,
        label: str | None = None,
    ) -> None:
        self.rect = rect
        self.value = max(0.0, min(1.0, value))
        self.on_change = on_change
        self.font = font
        self.label = label
        self.dragging = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_pos(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_pos(event.pos[0])

    def _set_from_pos(self, x: int) -> None:
        t = (x - self.rect.left) / self.rect.width
        self.value = max(0.0, min(1.0, t))
        self.on_change(self.value)

    def update(self, dt: float) -> None:
        _ = dt

    def draw(self, screen: pygame.Surface) -> None:
        # Track
        pygame.draw.rect(screen, (70, 80, 100), self.rect, border_radius=6)
        fill_rect = pygame.Rect(self.rect.left, self.rect.top, int(self.rect.width * self.value), self.rect.height)
        pygame.draw.rect(screen, (120, 180, 255), fill_rect, border_radius=6)
        # Knob
        knob_x = self.rect.left + int(self.rect.width * self.value)
        knob_rect = pygame.Rect(knob_x - 6, self.rect.centery - 10, 12, 20)
        pygame.draw.rect(screen, (240, 240, 255), knob_rect, border_radius=4)
        if self.font and self.label:
            text = self.font.render(f"{self.label}: {self.value:.2f}", True, (220, 230, 240))
            screen.blit(text, (self.rect.left, self.rect.top - text.get_height() - 4))
