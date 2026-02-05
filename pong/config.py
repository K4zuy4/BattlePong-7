"""Central configuration for the game.

Keep all balancing values here to make experimentation easier.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayConfig:
    width: int = 960
    height: int = 540
    title: str = "Battle Pong Template"
    fps: int = 60


@dataclass(frozen=True)
class PaddleConfig:
    width: int = 16
    height: int = 110
    speed: float = 420.0
    margin_x: int = 32


@dataclass(frozen=True)
class BallConfig:
    size: int = 16
    speed: float = 300.0
    max_bounce_angle_deg: float = 65.0


@dataclass(frozen=True)
class MatchConfig:
    win_score: int = 10


DISPLAY = DisplayConfig()
PADDLE = PaddleConfig()
BALL = BallConfig()
MATCH = MatchConfig()
