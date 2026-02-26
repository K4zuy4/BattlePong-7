from __future__ import annotations

import math
from pong.effects.base import EffectBase, EffectContext


class Effect(EffectBase):
    id = "turbo_speed"
    meta = {"name": "Turbo", "desc": "Everything moves 1.5x faster", "duration": 10.0}

    def __init__(self):
        self.time_left = self.meta.get("duration", 10.0)
        self.mult = 1.5

    def on_start(self, ctx: EffectContext) -> None:
        ctx.play_scene.ball["vx"] *= self.mult
        ctx.play_scene.ball["vy"] *= self.mult
        for p in ctx.play_scene.paddles.values():
            p["speed"] *= self.mult
        ctx.logger.info("Chaos Turbo start")

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        self.time_left -= dt
        if self.time_left <= 0:
            ctx.play_scene.managers["chaos"].deactivate(self.id)

    def on_end(self, ctx: EffectContext) -> None:
        inv = 1 / self.mult
        ctx.play_scene.ball["vx"] *= inv
        ctx.play_scene.ball["vy"] *= inv
        for p in ctx.play_scene.paddles.values():
            p["speed"] *= inv
        ctx.logger.info("Chaos Turbo end")


effect = Effect()


def get_effect():
    return Effect()
