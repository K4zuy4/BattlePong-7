from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Dict

from .base import EffectBase

log = logging.getLogger(__name__)


def load_effects(directory: str) -> Dict[str, EffectBase]:
    """Load all effect modules from a directory (path or package folder)."""
    base = Path(directory)
    effects: Dict[str, EffectBase] = {}
    if not base.exists():
        return effects
    for file in base.iterdir():
        if not file.is_file() or file.suffix != ".py" or file.name.startswith("__"):
            continue
        spec = importlib.util.spec_from_file_location(f"effects.{file.stem}", file)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore
        except Exception as exc:
            log.warning("Effect load failed", extra={"file": str(file), "error": str(exc)})
            continue
        effect = None
        if hasattr(module, "get_effect"):
            try:
                effect = module.get_effect()
            except Exception as exc:
                log.warning("get_effect failed", extra={"file": str(file), "error": str(exc)})
                continue
        elif hasattr(module, "effect"):
            effect = module.effect
        # auto instantiate class named Effect if present
        elif hasattr(module, "Effect"):
            try:
                effect = module.Effect()
            except Exception as exc:
                log.warning("Effect class init failed", extra={"file": str(file), "error": str(exc)})
                continue
        if not isinstance(effect, EffectBase):
            log.warning("Effect skipped (no EffectBase)", extra={"file": str(file)})
            continue
        if not getattr(effect, "id", ""):
            log.warning("Effect skipped (missing id)", extra={"file": str(file)})
            continue
        effects[effect.id] = effect
        log.info("Effect loaded", extra={"id": effect.id, "file": str(file)})
    return effects
