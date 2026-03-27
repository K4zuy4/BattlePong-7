from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext


class Effect(EffectBase):
    id = "ghost_paddle"
    meta = {"name": "Ghost Paddle", "desc": "Your paddle flickers in and out of view.", "duration": 10.0}

    def __init__(self) -> None:
        self.time_left = float(self.meta.get("duration", 10.0))
        self.active = False
        self.toggle_in = 0.0

    def on_start(self, ctx: EffectContext) -> None:
        self.active = True
        self.time_left = float(self.meta.get("duration", 10.0))
        self.toggle_in = 0.25
        ctx.play_scene.set_ghost_paddle_enabled(True)
        ctx.play_scene.set_ghost_paddle_visible(True)
        ctx.play_scene.set_ghost_toggle_in(self.toggle_in)

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if not self.active:
            return
        self.time_left -= dt
        self.toggle_in -= dt
        if self.toggle_in <= 0.0:
            current = bool(ctx.play_scene.match_modifiers["ghost_paddle_visible"])
            ctx.play_scene.set_ghost_paddle_visible(not current)
            self.toggle_in = ctx.rng.uniform(0.16, 0.55)
            ctx.play_scene.set_ghost_toggle_in(self.toggle_in)
        if self.time_left <= 0.0:
            ctx.play_scene.managers["chaos"].deactivate(self.id)

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        self.toggle_in = 0.0
        ctx.play_scene.set_ghost_paddle_enabled(False)
        ctx.play_scene.set_ghost_paddle_visible(True)
        ctx.play_scene.set_ghost_toggle_in(0.0)

    def reset_state(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = float(self.meta.get("duration", 10.0))
        self.toggle_in = 0.0
        ctx.play_scene.set_ghost_paddle_enabled(False)
        ctx.play_scene.set_ghost_paddle_visible(True)
        ctx.play_scene.set_ghost_toggle_in(0.0)


effect = Effect()


def get_effect() -> Effect:
    return Effect()
