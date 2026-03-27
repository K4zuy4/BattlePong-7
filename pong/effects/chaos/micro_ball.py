from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext


class Effect(EffectBase):
    id = "micro_ball"
    meta = {"name": "Micro Ball", "desc": "The ball becomes much smaller.", "duration": 10.0}

    def __init__(self) -> None:
        self.time_left = float(self.meta.get("duration", 10.0))
        self.active = False
        self.scale = 0.6

    def on_start(self, ctx: EffectContext) -> None:
        self.active = True
        self.time_left = float(self.meta.get("duration", 10.0))
        ctx.play_scene.set_ball_size_scale(self.scale)

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0.0:
            ctx.play_scene.managers["chaos"].deactivate(self.id)

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        ctx.play_scene.set_ball_size_scale(1.0)

    def reset_state(self, ctx: EffectContext) -> None:
        ctx.play_scene.set_ball_size_scale(1.0)
        self.active = False
        self.time_left = float(self.meta.get("duration", 10.0))


effect = Effect()


def get_effect() -> Effect:
    return Effect()
