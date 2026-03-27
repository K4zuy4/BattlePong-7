from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext


class Effect(EffectBase):
    id = "heavy_ball"
    meta = {"name": "Heavy Ball", "desc": "Weaker angle effect and higher ball speed.", "duration": 10.0}

    def __init__(self) -> None:
        self.time_left = float(self.meta.get("duration", 10.0))
        self.active = False
        self.speed_factor = 1.25
        self.bounce_scale = 0.55

    def on_start(self, ctx: EffectContext) -> None:
        self.active = True
        self.time_left = float(self.meta.get("duration", 10.0))
        ctx.play_scene.set_ball_speed_factor(self.speed_factor)
        ctx.play_scene.set_bounce_angle_scale(self.bounce_scale)

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0.0:
            ctx.play_scene.managers["chaos"].deactivate(self.id)

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        ctx.play_scene.set_ball_speed_factor(1.0)
        ctx.play_scene.set_bounce_angle_scale(1.0)

    def reset_state(self, ctx: EffectContext) -> None:
        ctx.play_scene.set_ball_speed_factor(1.0)
        ctx.play_scene.set_bounce_angle_scale(1.0)
        self.active = False
        self.time_left = float(self.meta.get("duration", 10.0))


effect = Effect()


def get_effect() -> Effect:
    return Effect()
