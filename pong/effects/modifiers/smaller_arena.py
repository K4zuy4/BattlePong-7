from __future__ import annotations

from pong.effects.base import EffectBase, EffectContext


class Effect(EffectBase):
    id = "smaller_arena"
    meta = {"name": "Smaller Arena", "desc": "Reduces playfield to 85% size."}

    def __init__(self):
        self._saved = None

    def on_start(self, ctx: EffectContext) -> None:
        ps = ctx.play_scene
        self._saved = (ps.width, ps.height, ps.margin)
        ps.width = int(ps.width * 0.85)
        ps.height = int(ps.height * 0.85)
        ps.margin = int(ps.margin * 0.9)
        # reposition paddles
        ps.paddles["left"]["x"] = ps.margin
        ps.paddles["right"]["x"] = ps.width - ps.margin - ps.pad_w
        ctx.logger.info("Effect smaller_arena applied", extra={"w": ps.width, "h": ps.height})

    def on_end(self, ctx: EffectContext) -> None:
        if not self._saved:
            return
        ps = ctx.play_scene
        ps.width, ps.height, ps.margin = self._saved
        ps.paddles["left"]["x"] = ps.margin
        ps.paddles["right"]["x"] = ps.width - ps.margin - ps.pad_w
        ctx.logger.info("Effect smaller_arena reverted")


effect = Effect()


def get_effect():
    return Effect()
