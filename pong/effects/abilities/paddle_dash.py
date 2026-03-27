from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext

EPSILON = 1e-4


class Effect(EffectBase):
    id = "paddle_dash"
    meta = {
        "name": "Paddle Dash",
        "desc": "Quick burst in the current movement direction.",
        "cooldown": 4.0,
        "duration": 0.18,
    }

    def __init__(self) -> None:
        self.active = False
        self.time_left = 0.0
        self.cooldown_remaining = 0.0
        self.dash_speed = 1250.0

    def can_activate(self, ctx: EffectContext) -> bool:
        return not self.active and self.cooldown_remaining <= EPSILON

    def on_activate(self, ctx: EffectContext) -> None:
        if not self.can_activate(ctx):
            return
        self.active = True
        self.time_left = float(self.meta.get("duration", 0.18))
        self.cooldown_remaining = float(self.meta.get("cooldown", 4.0))
        direction = ctx.play_scene.resolve_dash_direction()
        ctx.play_scene.start_left_paddle_dash(direction=direction, speed=self.dash_speed, duration=self.time_left)
        ctx.logger.info("Ability activated", extra={"ability": self.id, "direction": direction})

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if self.cooldown_remaining > 0.0:
            self.cooldown_remaining = max(0.0, self.cooldown_remaining - dt)
            if self.cooldown_remaining <= EPSILON:
                self.cooldown_remaining = 0.0
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0.0:
            ctx.play_scene.managers["abilities"].deactivate(self.id)

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        ctx.play_scene.stop_left_paddle_dash()

    def reset_state(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        self.cooldown_remaining = 0.0
        ctx.play_scene.stop_left_paddle_dash()


effect = Effect()


def get_effect() -> Effect:
    return Effect()
