"""Sprite/Skin loader and drawing helpers."""

from __future__ import annotations

import os
import logging
from typing import Optional

import pygame

from pong.settings import RuntimeSettings
from pong.events import SettingsChanged

logger = logging.getLogger(__name__)


class SkinManager:
    def __init__(self, bus, settings: RuntimeSettings) -> None:
        self.bus = bus
        self.settings = settings
        self.ball_surface: Optional[pygame.Surface] = None
        self.paddle_surface: Optional[pygame.Surface] = None
        self.background_surface: Optional[pygame.Surface] = None
        self._scaled_background: Optional[pygame.Surface] = None

        bus.subscribe(SettingsChanged, self._on_settings_changed)
        self._reload_all()

    def _load_surface(self, path: Optional[str]) -> Optional[pygame.Surface]:
        if not path:
            return None
        if not os.path.isfile(path):
            return None
        return pygame.image.load(path).convert_alpha()

    def _reload_all(self) -> None:
        sprites = self.settings.sprites
        self.ball_surface = self._load_surface(sprites.ball_image)
        self.paddle_surface = self._load_surface(sprites.paddle_image)
        self.background_surface = self._load_surface(sprites.background_image)
        self._scaled_background = None
        logger.info(
            "Skins reloaded",
            extra={
                "ball": sprites.ball_image,
                "paddle": sprites.paddle_image,
                "background": sprites.background_image,
            },
        )

    def _on_settings_changed(self, event: SettingsChanged) -> None:
        if event.section in {"sprites", "display"}:
            self._reload_all()

    def draw_background(self, screen: pygame.Surface) -> bool:
        if not self.background_surface:
            return False
        disp = self.settings.display
        if self.settings.sprites.tile_background:
            tex = self.background_surface
            tex_w, tex_h = tex.get_size()
            for x in range(0, disp.width, tex_w):
                for y in range(0, disp.height, tex_h):
                    screen.blit(tex, (x, y))
        else:
            if (
                self._scaled_background is None
                or self._scaled_background.get_width() != disp.width
                or self._scaled_background.get_height() != disp.height
            ):
                self._scaled_background = pygame.transform.smoothscale(
                    self.background_surface, (disp.width, disp.height)
                )
            screen.blit(self._scaled_background, (0, 0))
        return True

    def draw_paddle(self, paddle, screen: pygame.Surface) -> bool:
        if not self.paddle_surface:
            return False
        paddles = self.settings.paddle
        sprite = pygame.transform.smoothscale(
            self.paddle_surface, (paddles.width, paddles.height)
        )
        screen.blit(sprite, (paddle.x, paddle.y))
        return True

    def draw_ball(self, ball, screen: pygame.Surface) -> bool:
        if not self.ball_surface:
            return False
        size = self.settings.ball.size
        sprite = pygame.transform.smoothscale(self.ball_surface, (size, size))
        sprite = self._apply_circle_mask(sprite)

        if self.settings.sprites.ball_rotation_speed != 0:
            sprite = pygame.transform.rotate(sprite, ball.rotation_angle)
            rect = sprite.get_rect(center=(ball.x + size / 2, ball.y + size / 2))
        else:
            rect = sprite.get_rect(topleft=(ball.x, ball.y))

        screen.blit(sprite, rect.topleft)
        return True

    @staticmethod
    def _apply_circle_mask(surface: pygame.Surface) -> pygame.Surface:
        size = surface.get_width()
        masked = surface.copy()
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
        masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return masked
