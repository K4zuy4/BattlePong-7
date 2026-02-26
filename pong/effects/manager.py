from __future__ import annotations

import logging
import random
from typing import Dict, List

from .base import EffectBase, EffectContext
from .loader import load_effects


class EffectManager:
    def __init__(self, category: str, paths: list[str], ctx: EffectContext) -> None:
        self.category = category
        self.ctx = ctx
        self.registry: Dict[str, EffectBase] = {}
        self.active: Dict[str, EffectBase] = {}
        self.log = logging.getLogger(__name__ + f".{category}")
        self._load(paths)

    def _load(self, paths: list[str]) -> None:
        for p in paths:
            effects = load_effects(p)
            for id_, eff in effects.items():
                if id_ in self.registry:
                    continue
                # fresh instance per registry
                self.registry[id_] = eff
                eff.on_register(self.ctx)
        self.log.info("Effects registered", extra={"category": self.category, "count": len(self.registry)})

    def activate(self, effect_id: str) -> None:
        eff = self.registry.get(effect_id)
        if not eff:
            return
        if effect_id in self.active:
            return
        # single-use: remove from registry after activation
        single_use = getattr(eff, "single_use", False) or getattr(eff, "meta", {}).get("single_use", False)
        self.active[effect_id] = eff
        # Boosts use on_activate, others use on_start
        if self.category == "boosts" and hasattr(eff, "on_activate"):
            eff.on_activate(self.ctx)  # type: ignore
        else:
            eff.on_start(self.ctx)
        self.log.info("Effect start", extra={"category": self.category, "id": effect_id})
        if single_use:
            self.registry.pop(effect_id, None)

    def deactivate(self, effect_id: str) -> None:
        eff = self.active.pop(effect_id, None)
        if not eff:
            return
        try:
            eff.on_end(self.ctx)
        finally:
            self.log.info("Effect end", extra={"category": self.category, "id": effect_id})

    def activate_all(self) -> None:
        for eid in list(self.registry.keys()):
            self.activate(eid)

    def on_tick(self, dt: float) -> None:
        for eff in list(self.active.values()):
            try:
                eff.on_tick(self.ctx, dt)
            except Exception as exc:
                self.log.exception("Effect tick failed", extra={"id": eff.id, "error": str(exc)})

    def on_event(self, event) -> None:
        for eff in list(self.active.values()):
            try:
                eff.on_event(self.ctx, event)
            except Exception as exc:
                self.log.exception("Effect event failed", extra={"id": eff.id, "error": str(exc)})
