"""Lightweight particle effects for hits and goals."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

import pygame

from pong.settings import RuntimeSettings


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.vy += 60 * dt  # light gravity


class ParticleSystem:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.particles: List[Particle] = []

    def spawn_burst(self, x: float, y: float, color: tuple[int, int, int], amount: int = 12) -> None:
        for _ in range(amount):
            speed = random.uniform(80, 240)
            angle = random.uniform(0, 360)
            vx = speed * pygame.math.Vector2(1, 0).rotate(angle).x
            vy = speed * pygame.math.Vector2(1, 0).rotate(angle).y
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=vx,
                    vy=vy,
                    life=random.uniform(0.4, 0.9),
                    size=random.uniform(3, 6),
                    color=color,
                )
            )

    def update(self, dt: float) -> None:
        for p in list(self.particles):
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, screen: pygame.Surface) -> None:
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p.life / 0.9))))
            surf = pygame.Surface((p.size, p.size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p.color, alpha), (p.size / 2, p.size / 2), p.size / 2)
            screen.blit(surf, (p.x, p.y))

