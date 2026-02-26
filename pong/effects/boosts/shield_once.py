from __future__ import annotations

import pygame
from pong.effects.base import EffectBase, EffectContext
from pong.events import BallBouncePaddle


class Effect(EffectBase):
    id = "shield_once"
    meta = {"name": "Shield", "desc": "5s goal shield", "duration": 5.0, "single_use": True}

    def __init__(self):
        self.time_left = 0.0
        self.active = False
        self.color = (120, 200, 255)
        self.alpha = 160

    def can_activate(self, ctx: EffectContext) -> bool:
        return not self.active

    def on_activate(self, ctx: EffectContext) -> None:
        self.time_left = self.meta.get("duration", 5.0)
        self.active = True
        ctx.logger.info("Shield active", extra={"duration": self.time_left})
        # explicit log event name for visibility
        if ctx.bus:
            from pong.events import GameEvent
            class ShieldLog(GameEvent):
                def __init__(self, msg): self.msg = msg
            ctx.bus.publish(ShieldLog(f"Shield activated ({self.time_left:.1f}s)"))

    def on_event(self, ctx: EffectContext, event) -> None:
        # no-op; handled in draw and ball logic
        return

    def on_tick(self, ctx: EffectContext, dt: float) -> None:
        if not self.active:
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.active = False
            ctx.play_scene.managers["boosts"].deactivate(self.id)
            ctx.logger.info("Shield expired")

    def on_end(self, ctx: EffectContext) -> None:
        self.active = False

    # Helper for play scene rendering
    def draw_overlay(self, ctx: EffectContext, screen: pygame.Surface) -> None:
        if not self.active:
            return
        margin = ctx.play_scene.margin
        h = ctx.play_scene.height
        rect = pygame.Rect(0, 0, margin + 6, h)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        surf.fill((*self.color, self.alpha))
        screen.blit(surf, rect)


effect = Effect()


def get_effect():
    return Effect()
