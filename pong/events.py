"""Typed event system to decouple gameplay systems.

Gameplay features (powerups, modifiers, UI, analytics) can subscribe to events
without changing the core game loop.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, DefaultDict, Generic, TypeVar, Optional


class GameEvent:
    """Base class for all domain events."""


@dataclass(frozen=True)
class BallHitPaddle(GameEvent):
    paddle_id: str


@dataclass(frozen=True)
class PointScored(GameEvent):
    scorer_id: str  # "left" or "right"
    left_score: int
    right_score: int


@dataclass(frozen=True)
class RoundReset(GameEvent):
    pass


@dataclass(frozen=True)
class SettingsChangeRequested(GameEvent):
    """Ask the game to patch runtime settings."""

    section: str
    values: dict[str, object]


@dataclass(frozen=True)
class SettingsChanged(GameEvent):
    """Broadcast after settings were applied."""

    section: str
    values: dict[str, object]


@dataclass(frozen=True)
class SpawnBallRequested(GameEvent):
    """Ask the game to spawn more balls."""

    count: int = 1
    speed: float | None = None
    size: int | None = None


@dataclass(frozen=True)
class BallSpawned(GameEvent):
    ball_id: str


@dataclass(frozen=True)
class BallRemoved(GameEvent):
    ball_id: str


@dataclass(frozen=True)
class KeyAction(GameEvent):
    key: int
    action: str  # "down" | "up"
    mods: int


@dataclass(frozen=True)
class BallBouncePaddle(GameEvent):
    ball_id: str
    paddle_id: str
    hit_pos: float
    speed: float
    spin: float
    vx: float
    vy: float
    angle_deg: float


@dataclass(frozen=True)
class BallBounceWall(GameEvent):
    ball_id: str
    wall: str  # "top" | "bottom" | "left" | "right"
    speed: float
    spin: float
    vx: float
    vy: float
    angle_deg: float


@dataclass(frozen=True)
class SceneChanged(GameEvent):
    previous: str | None
    current: str


@dataclass(frozen=True)
class ResolutionChanged(GameEvent):
    width: int
    height: int
    prev_width: int
    prev_height: int


EventType = TypeVar("EventType", bound=GameEvent)
Listener = Callable[[GameEvent], None]


class EventBus(Generic[EventType]):
    def __init__(self) -> None:
        self._listeners: DefaultDict[type[GameEvent], list[tuple[Listener, Optional[Callable[[GameEvent], bool]]]]] = defaultdict(list)
        import logging
        self._log = logging.getLogger(__name__)
        self.log_events = True

    def subscribe(self, event_cls: type[GameEvent], listener: Listener, predicate: Callable[[GameEvent], bool] | None = None) -> None:
        self._listeners[event_cls].append((listener, predicate))
        self._log.debug(
            "Event subscribed",
            extra={"event": event_cls.__name__, "listener": getattr(listener, "__name__", str(listener))},
        )

    def unsubscribe(self, event_cls: type[GameEvent], listener: Listener) -> None:
        lst = self._listeners.get(event_cls, [])
        self._listeners[event_cls] = [(l, p) for (l, p) in lst if l != listener]

    def emit(self, event: GameEvent) -> None:
        self.publish(event)

    def publish(self, event: GameEvent) -> None:
        etype = type(event)
        if self.log_events:
            payload = {**event.__dict__}
            self._log.info("Event %s %s", etype.__name__, payload, extra={"event": etype.__name__, "payload": payload})
        # direct listeners and wildcard (GameEvent)
        listeners = list(self._listeners.get(etype, [])) + list(self._listeners.get(GameEvent, []))
        for listener, predicate in listeners:
            if predicate and not predicate(event):
                continue
            try:
                listener(event)
            except Exception as exc:  # keep game running
                self._log.exception("Event handler error", extra={"event": etype.__name__, "listener": str(listener), "error": str(exc)})
