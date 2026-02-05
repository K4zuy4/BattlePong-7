"""Runtime settings that can be patched at any time.

All gameplay-relevant numbers live here instead of hard-coded globals.
Other systems can request changes via events and the game will apply them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DisplaySettings:
    width: int = 960
    height: int = 540
    title: str = "Battle Pong"
    fps: int = 60


@dataclass
class PaddleSettings:
    width: int = 16
    height: int = 110
    speed: float = 420.0
    margin_x: int = 32


@dataclass
class BallSettings:
    size: int = 16
    speed: float = 300.0
    max_bounce_angle_deg: float = 65.0
    count_on_reset: int = 1


@dataclass
class SpriteSettings:
    """Paths to optional sprite assets."""

    ball_image: str | None = None
    paddle_image: str | None = None
    background_image: str | None = None
    ball_rotation_speed: float = 180.0  # degrees per second
    tile_background: bool = False


@dataclass
class AudioSettings:
    master_volume: float = 1.0
    sfx_volume: float = 1.0
    screen_shake: float = 0.5


@dataclass
class TrailSettings:
    effect: str = "trail_none"


@dataclass
class MatchSettings:
    win_score: int = 10


@dataclass
class RuntimeSettings:
    display: DisplaySettings = field(default_factory=DisplaySettings)
    paddle: PaddleSettings = field(default_factory=PaddleSettings)
    ball: BallSettings = field(default_factory=BallSettings)
    sprites: SpriteSettings = field(default_factory=SpriteSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    trail: TrailSettings = field(default_factory=TrailSettings)
    match: MatchSettings = field(default_factory=MatchSettings)

    def patch(self, section: str, **values: Any) -> Dict[str, Any]:
        """Update values on one settings section and return the applied changes."""
        target = getattr(self, section, None)
        if target is None:
            raise ValueError(f"Unknown settings section '{section}'")

        applied: Dict[str, Any] = {}
        for key, value in values.items():
            if not hasattr(target, key):
                raise ValueError(f"Unknown field '{key}' for section '{section}'")
            setattr(target, key, value)
            applied[key] = value
        logger.info("Settings patched", extra={"section": section, "values": applied})
        return applied
