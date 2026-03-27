from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext


class Effect(EffectBase):
    id = "input_swap"
    meta = {"name": "Input Swap", "desc": "Up and down are inverted.", "duration": 10.0}

    def __init__(self) -> None:
        self.time_left = float(self.meta.get("duration", 10.0))
        self.active = False

    def on_start(self, ctx: EffectContext) -> None:
        self.active = True
        self.time_left = float(self.meta.get("duration", 10.0))
        ctx.play_scene.set_invert_input(True)

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0.0:
            ctx.play_scene.managers["chaos"].deactivate(self.id)

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        ctx.play_scene.set_invert_input(False)

    def reset_state(self, ctx: EffectContext) -> None:
        ctx.play_scene.set_invert_input(False)
        self.active = False
        self.time_left = float(self.meta.get("duration", 10.0))


effect = Effect()


def get_effect() -> Effect:
    return Effect()
