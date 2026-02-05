"""Optional game systems that manipulate runtime settings via events.

These are meant as examples for how to drive the game dynamically.
"""

from __future__ import annotations

import random

from pong.events import SettingsChangeRequested, SpawnBallRequested
from pong.settings import RuntimeSettings


class ChaosSystem:
    """Periodically tweaks ball settings and spawns new balls."""

    def __init__(self, bus, settings: RuntimeSettings, interval: float = 7.0) -> None:
        self.bus = bus
        self.settings = settings
        self.interval = interval
        self.elapsed = 0.0
        self.enabled = True

    def update(self, dt: float) -> None: 
        if not self.enabled:
            return
        self.elapsed += dt
        if self.elapsed < self.interval:
            return
        self.elapsed = 0.0

        speed_variation = self.settings.ball.speed * random.uniform(0.85, 1.3)
        size_variation = int(max(8, min(32, self.settings.ball.size * random.uniform(0.8, 1.2))))

        self.bus.publish(
            SettingsChangeRequested(
                section="ball",
                values={"speed": speed_variation, "size": size_variation},
            )
        )
        self.bus.publish(SpawnBallRequested(count=1))

