from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


@dataclass
class EffectContext:
    app: Any
    play_scene: Any
    bus: Any
    logger: logging.Logger
    rng: Any


class EffectBase:
    id: str = ""
    meta: dict[str, Any] = {}

    def on_register(self, ctx: EffectContext) -> None:
        """Called after loading; can subscribe to bus."""
        return

    def on_start(self, ctx: EffectContext) -> None:
        """Effect becomes active."""
        return

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        return

    def on_event(self, ctx: EffectContext, event: Any) -> None:
        return

    def on_end(self, ctx: EffectContext) -> None:
        """Cleanup, restore changes."""
        return

    # Boost-specific
    def can_activate(self, ctx: EffectContext) -> bool:
        return True

    def on_activate(self, ctx: EffectContext) -> None:
        return
