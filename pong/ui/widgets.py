"""Minimal UI widgets for menus."""

from __future__ import annotations

import pygame
import logging

logger = logging.getLogger(__name__)


class Button:
    def __init__(self, rect: pygame.Rect, label: str, font: pygame.font.Font, on_click) -> None:
        self.rect = rect
        self.label = label
        self.font = font
        self.on_click = on_click
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                logger.debug("Button click", extra={"label": self.label})

    def draw(self, screen: pygame.Surface) -> None:
        base = (60, 70, 90)
        hover = (90, 110, 140)
        color = hover if self.hovered else base
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, width=2, border_radius=8)
        text = self.font.render(self.label, True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)


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

class Label:
    def __init__(self, text: str, pos: tuple[int, int], font: pygame.font.Font, color=(230, 230, 230)) -> None:
        self.text = text
        self.pos = pos
        self.font = font
        self.color = color

    def draw(self, screen: pygame.Surface) -> None:
        img = self.font.render(self.text, True, self.color)
        screen.blit(img, self.pos)
