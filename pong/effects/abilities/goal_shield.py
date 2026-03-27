from __future__ import annotations

import pygame

from pong.effects.base import EffectBase, EffectContext

EPSILON = 1e-4


class Effect(EffectBase):
    id = "goal_shield"
    meta = {
        "name": "Goal Shield",
        "desc": "Blocks your goal for a short time.",
        "cooldown": 9.0,
        "duration": 3.5,
    }

    def __init__(self) -> None:
        self.active = False
        self.time_left = 0.0
        self.cooldown_remaining = 0.0
        self.color = (120, 200, 255)
        self.alpha = 160

    def can_activate(self, ctx: EffectContext) -> bool:
        return not self.active and self.cooldown_remaining <= EPSILON

    def on_activate(self, ctx: EffectContext) -> None:
        if not self.can_activate(ctx):
            return
        self.active = True
        self.time_left = float(self.meta.get("duration", 3.5))
        self.cooldown_remaining = float(self.meta.get("cooldown", 9.0))
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

    def reset_state(self, ctx: EffectContext) -> None:
        self.active = False
        self.time_left = 0.0
        self.cooldown_remaining = 0.0

    def draw_overlay(self, ctx: EffectContext, screen: pygame.Surface) -> None:
        if not self.active:
            return
        margin = ctx.play_scene.margin
        rect = pygame.Rect(0, 0, margin + 8, ctx.play_scene.height)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        surf.fill((*self.color, self.alpha))
        screen.blit(surf, rect)


effect = Effect()


def get_effect() -> Effect:
    return Effect()
