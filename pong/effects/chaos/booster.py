from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext


class Effect(EffectBase):
    id = "booster"
    meta = {"name": "Booster Zones", "desc": "The ball gets faster inside marked arena zones.", "duration": 10.0}

    def __init__(self) -> None:
        self.time_left = float(self.meta.get("duration", 10.0))
        self.active = False

    def on_start(self, ctx: EffectContext) -> None:
        self.active = True
        self.time_left = float(self.meta.get("duration", 10.0))
        play = ctx.play_scene
        zones = []
        zone_width = int(play.width * 0.16)
        zone_height = int(play.play_height * 0.22)
        for _ in range(3):
            x = ctx.rng.randint(play.margin + 80, max(play.margin + 80, play.width - play.margin - zone_width - 80))
            y = ctx.rng.randint(play.play_top + 30, max(play.play_top + 30, play.play_bottom - zone_height - 30))
            zones.append({"x": x, "y": y, "w": zone_width, "h": zone_height})
        play.set_booster_zones(zones)

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0.0:
            ctx.play_scene.managers["chaos"].deactivate(self.id)

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        ctx.play_scene.set_booster_zones([])

    def reset_state(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = float(self.meta.get("duration", 10.0))
        ctx.play_scene.set_booster_zones([])


effect = Effect()


def get_effect() -> Effect:
    return Effect()
