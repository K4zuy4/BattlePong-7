"""Powerup framework.

Add new powerups by subclassing `PowerupEffect` and registering in `PowerupManager`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable

import pygame

from pong.config import DISPLAY
from pong.entities import Paddle
from pong.events import BallHitPaddle, EventBus, PointScored


class PowerupEffect:
    """Base class for all powerup logic."""

    name = "base"

    def on_attach(self, bus: EventBus) -> None:
        """Subscribe to events and initialize state."""

    def update(self, dt: float) -> None:
        """Update timers and temporary modifiers."""

    def draw(self, screen: pygame.Surface) -> None:
        """Optional debug/UI drawing."""


@dataclass
class SpeedBoostPowerup(PowerupEffect):
    """Sample powerup: temporarily increases paddle speed after a hit."""

    left: Paddle
    right: Paddle
    boost_duration: float = 1.2
    boost_factor: float = 1.6

    name = "speed_boost"

    def __post_init__(self) -> None:
        self._timers = {self.left.paddle_id: 0.0, self.right.paddle_id: 0.0}

    def on_attach(self, bus: EventBus) -> None:
        bus.subscribe(BallHitPaddle, self._on_hit)
        bus.subscribe(PointScored, self._on_point_scored)

    def _on_hit(self, event: BallHitPaddle) -> None:
        self._timers[event.paddle_id] = self.boost_duration

    def _on_point_scored(self, _event: PointScored) -> None:
        for paddle in (self.left, self.right):
            paddle.speed_multiplier = 1.0
            self._timers[paddle.paddle_id] = 0.0

    def update(self, dt: float) -> None:
        for paddle in (self.left, self.right):
            pid = paddle.paddle_id
            self._timers[pid] = max(0.0, self._timers[pid] - dt)
            paddle.speed_multiplier = self.boost_factor if self._timers[pid] > 0 else 1.0


class PowerupManager:
    """Owns and updates active powerups.

    Keep this small so you can later add spawn rules, rarity, pickup objects, etc.
    """

    def __init__(self, bus: EventBus, effects: Iterable[PowerupEffect] | None = None) -> None:
        self.bus = bus
        self.effects = list(effects or [])

        for effect in self.effects:
            effect.on_attach(bus)

    def update(self, dt: float) -> None:
        for effect in self.effects:
            effect.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        for effect in self.effects:
            effect.draw(screen)

    @classmethod
    def with_default_template(cls, bus: EventBus, left: Paddle, right: Paddle) -> "PowerupManager":
        effects: list[PowerupEffect] = [SpeedBoostPowerup(left, right)]

        random.shuffle(effects)
        return cls(bus, effects)
