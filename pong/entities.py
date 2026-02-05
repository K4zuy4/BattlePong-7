"""Entities and physics primitives."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from pong.settings import RuntimeSettings


@dataclass
class Paddle:
    paddle_id: str
    x: float
    y: float
    up_key: int
    down_key: int
    settings: RuntimeSettings
    color: tuple[int, int, int] = (240, 240, 240)
    speed_multiplier: float = 1.0

    @property
    def rect(self) -> pygame.Rect:
        paddles = self.settings.paddle
        return pygame.Rect(int(self.x), int(self.y), paddles.width, paddles.height)

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        direction = 0
        if keys[self.up_key]:
            direction -= 1
        if keys[self.down_key]:
            direction += 1

        paddles = self.settings.paddle
        display = self.settings.display
        self.y += direction * paddles.speed * self.speed_multiplier * dt
        self.y = max(0, min(display.height - paddles.height, self.y))

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, self.color, self.rect, border_radius=4)


@dataclass
class Ball:
    ball_id: str
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    settings: RuntimeSettings
    color: tuple[int, int, int] = (255, 225, 150)
    rotation_angle: float = 0.0

    @property
    def rect(self) -> pygame.Rect:
        size = self.settings.ball.size
        return pygame.Rect(int(self.x), int(self.y), size, size)

    def update(self, dt: float) -> None:
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt

    def bounce_vertical(self) -> None:
        self.velocity_y *= -1

    def bounce_from_paddle(self, paddle: Paddle) -> None:
        settings = self.settings
        paddle_settings = settings.paddle
        ball_settings = settings.ball
        center_ball = self.y + ball_settings.size / 2
        center_paddle = paddle.y + paddle_settings.height / 2
        relative_intersect = center_ball - center_paddle
        normalized = max(-1.0, min(1.0, relative_intersect / (paddle_settings.height / 2)))

        bounce_angle = math.radians(ball_settings.max_bounce_angle_deg) * normalized
        speed = math.hypot(self.velocity_x, self.velocity_y)
        new_speed_x = abs(speed * math.cos(bounce_angle))
        new_speed_y = speed * math.sin(bounce_angle)

        self.velocity_x = new_speed_x if self.velocity_x < 0 else -new_speed_x
        self.velocity_y = new_speed_y

        if self.velocity_x > 0:
            self.x = paddle.x + paddle_settings.width
        else:
            self.x = paddle.x - ball_settings.size

    def draw(self, screen: pygame.Surface) -> None:
        size = self.settings.ball.size
        center = (int(self.x + size / 2), int(self.y + size / 2))
        pygame.draw.circle(screen, self.color, center, size // 2)
