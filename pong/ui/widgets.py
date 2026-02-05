"""Minimal UI widgets for menus."""

from __future__ import annotations

import pygame


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

    def draw(self, screen: pygame.Surface) -> None:
        base = (60, 70, 90)
        hover = (90, 110, 140)
        color = hover if self.hovered else base
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, width=2, border_radius=8)
        text = self.font.render(self.label, True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)


class Label:
    def __init__(self, text: str, pos: tuple[int, int], font: pygame.font.Font, color=(230, 230, 230)) -> None:
        self.text = text
        self.pos = pos
        self.font = font
        self.color = color

    def draw(self, screen: pygame.Surface) -> None:
        img = self.font.render(self.text, True, self.color)
        screen.blit(img, self.pos)
