from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext
from pong.events import BallBouncePaddle


class Effect(EffectBase):
    id = "stun_ball"
    meta = {"name": "Stun Ball", "desc": "Paddle hits cause a short movement stun.", "duration": 10.0}

    def __init__(self) -> None:
        self.time_left = float(self.meta.get("duration", 10.0))
        self.active = False
        self.stun_duration = 0.5

    def on_start(self, ctx: EffectContext) -> None:
        self.active = True
        self.time_left = float(self.meta.get("duration", 10.0))

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0.0:
            ctx.play_scene.managers["chaos"].deactivate(self.id)

    def on_event(self, ctx: EffectContext, event) -> None:
        if not self.active:
            return
        if isinstance(event, BallBouncePaddle):
            ctx.play_scene.apply_paddle_stun(event.paddle_id, self.stun_duration)

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0

    def reset_state(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = float(self.meta.get("duration", 10.0))


effect = Effect()


def get_effect() -> Effect:
    return Effect()
