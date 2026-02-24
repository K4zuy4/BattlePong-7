from __future__ import annotations

import pygame
from dataclasses import dataclass
from typing import Callable


@dataclass
class DebugOverlayConfig:
    show: bool = True
    font_size: int = 16
    padding: int = 8
    bg: tuple[int, int, int, int] = (0, 0, 0, 140)
    fg: tuple[int, int, int] = (220, 240, 255)


class DebugOverlay:
    def __init__(self, config: DebugOverlayConfig | None = None) -> None:
        self.config = config or DebugOverlayConfig()
        self.font: pygame.font.Font | None = None
        self.lines_provider: Callable[[], list[str]] | None = None

    def set_provider(self, provider: Callable[[], list[str]]) -> None:
        self.lines_provider = provider

    def draw(self, screen: pygame.Surface) -> None:
        if not self.config.show or not self.lines_provider:
            return
        if self.font is None:
            self.font = pygame.font.SysFont("consolas", self.config.font_size)
        lines = self.lines_provider()
        if not lines:
            return
        pad = self.config.padding
        text_surfs = [self.font.render(line, True, self.config.fg) for line in lines]
        width = max(s.get_width() for s in text_surfs) + pad * 2
        height = sum(s.get_height() for s in text_surfs) + pad * 2 + (len(text_surfs) - 1) * 2
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill(self.config.bg)
        y = pad
        for surf in text_surfs:
            overlay.blit(surf, (pad, y))
            y += surf.get_height() + 2
        screen.blit(overlay, (pad, pad))
