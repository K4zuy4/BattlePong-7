"""Typed event system to decouple gameplay systems.

Gameplay features (powerups, modifiers, UI, analytics) can subscribe to events
without changing the core game loop.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, DefaultDict, Generic, TypeVar


class GameEvent:
    """Base class for all domain events."""


@dataclass(frozen=True)
class BallHitPaddle(GameEvent):
    paddle_id: str


@dataclass(frozen=True)
class PointScored(GameEvent):
    scorer_id: str


@dataclass(frozen=True)
class RoundReset(GameEvent):
    pass


EventType = TypeVar("EventType", bound=GameEvent)
Listener = Callable[[GameEvent], None]


class EventBus(Generic[EventType]):
    def __init__(self) -> None:
        self._listeners: DefaultDict[type[GameEvent], list[Listener]] = defaultdict(list)

    def subscribe(self, event_cls: type[GameEvent], listener: Listener) -> None:
        self._listeners[event_cls].append(listener)

    def publish(self, event: GameEvent) -> None:
        for listener in self._listeners[type(event)]:
            listener(event)
