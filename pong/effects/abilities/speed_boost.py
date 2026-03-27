from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext

EPSILON = 1e-4


class Effect(EffectBase):
    id = "speed_boost"
    meta = {
        "name": "Speed Boost",
        "desc": "Temporarily increases paddle movement speed.",
        "cooldown": 7.5,
        "duration": 2.75,
    }

    def __init__(self) -> None:
        self.active = False
        self.time_left = 0.0
        self.cooldown_remaining = 0.0
        self.speed_multiplier = 1.85

    def can_activate(self, ctx: EffectContext) -> bool:
        return not self.active and self.cooldown_remaining <= EPSILON

    def on_activate(self, ctx: EffectContext) -> None:
        if not self.can_activate(ctx):
            return
        self.active = True
        self.time_left = float(self.meta.get("duration", 2.75))
        self.cooldown_remaining = float(self.meta.get("cooldown", 7.5))
        ctx.play_scene.set_left_speed_multiplier(self.speed_multiplier)
        ctx.logger.info("Ability activated", extra={"ability": self.id})

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
        ctx.play_scene.set_left_speed_multiplier(1.0)

    def reset_state(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        self.cooldown_remaining = 0.0
        ctx.play_scene.set_left_speed_multiplier(1.0)


effect = Effect()


def get_effect() -> Effect:
    return Effect()
