from __future__ import annotations

"""Clock helpers: fixed update step + render delta interpolation."""

import pygame
from dataclasses import dataclass


@dataclass
class Timestep:
    fixed_dt: float = 1.0 / 120.0  # simulation step (seconds)
    max_frame_time: float = 0.25   # clamp to avoid spiral of death


class Clock:
    def __init__(self, timestep: Timestep | None = None) -> None:
        self.timestep = timestep or Timestep()
        self._accumulator = 0.0
        self.render_dt = 0.0
        self.alpha = 0.0
        self._pygame_clock = pygame.time.Clock()

    def tick(self, target_fps: int) -> None:
        # measure frame time
        frame_dt = self._pygame_clock.tick(target_fps) / 1000.0
        frame_dt = min(frame_dt, self.timestep.max_frame_time)
        self._accumulator += frame_dt
        self.render_dt = frame_dt

    def step_ready(self) -> bool:
        return self._accumulator >= self.timestep.fixed_dt

    def consume_step(self) -> float:
        self._accumulator -= self.timestep.fixed_dt
        self.alpha = self._accumulator / self.timestep.fixed_dt
        return self.timestep.fixed_dt

    @property
    def fps(self) -> float:
        return self._pygame_clock.get_fps()
