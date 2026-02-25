from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional
import pygame

from .transitions import TransitionController, TransitionSpec


class Scene:
    """Abstract scene interface."""

    def on_enter(self, payload: dict | None = None) -> None:
        pass

    def on_exit(self, payload: dict | None = None) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        raise NotImplementedError

    def handle_input(self, input_state) -> None:
        """Optional input processing (action-based) separate from raw events."""
        pass

    def on_event(self, event) -> None:
        """Domain events dispatched via EventBus."""
        pass

    def update(self, dt: float) -> None:
        raise NotImplementedError

    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError


@dataclass
class _StackItem:
    name: str
    scene: Scene
    payload: dict | None = None


class SceneManager:
    """Scene stack with push/pop and optional transitions."""

    def __init__(self) -> None:
        self._stack: list[_StackItem] = []
        self.scenes: dict[str, Scene] = {}
        self.log = logging.getLogger(__name__)
        self.transitions: TransitionController | None = None
        # default spec provider can be overridden per call
        self.transition_spec_provider: Optional[Callable[[], TransitionSpec]] = None
        self.app = None  # set by GameApp

    def attach_transitions(self, controller: TransitionController, spec_provider: Callable[[], TransitionSpec]) -> None:
        self.transitions = controller
        self.transition_spec_provider = spec_provider

    def register(self, name: str, scene: Scene) -> None:
        self.scenes[name] = scene
        self.log.debug("Scene registered", extra={"name": name})

    def set_scene(self, name: str, payload: dict | None = None) -> None:
        if self.current_name == name:
            return
        prev = self.current_name
        def action():
            self._replace_stack_with(name, payload)
            self._emit_scene_changed(prev, name)
        self._navigate(action, "set_scene", name)

    def push(self, name: str, payload: dict | None = None) -> None:
        prev = self.current_name
        def action():
            self._push(name, payload)
            self._emit_scene_changed(prev, name)
        self._navigate(action, "push", name)

    def pop(self, payload: dict | None = None) -> None:
        if not self._stack:
            return
        if len(self._stack) == 1:
            self.log.debug("Pop ignored; single scene on stack")
            return
        def apply_pop():
            popped = self._stack.pop()
            popped.scene.on_exit(payload)
            self.log.info("Scene pop", extra={"popped": popped.name})
            if self._stack:
                self.top.scene.on_enter(payload)
                self._emit_scene_changed(popped.name, self.current_name)

        if self.transitions and self.transition_spec_provider and not self.transitions.active:
            spec = self.transition_spec_provider()
            if spec.duration > 0:
                self.transitions.start(spec, apply_pop)
                self.log.info("Scene pop (transition)")
                return
        apply_pop()

    def _emit_scene_changed(self, previous: str | None, current: str | None) -> None:
        from pong.events import SceneChanged, GameEvent
        if self.app and hasattr(self.app, "bus"):
            try:
                self.app.bus.publish(SceneChanged(previous=previous, current=current))
            except Exception:
                self.log.exception("Failed to publish SceneChanged", extra={"previous": previous, "current": current})

    def _navigate(self, action: Callable[[], None], kind: str, target: str) -> None:
        """Optionally wrap navigation in a transition."""
        # Initial navigation: no stack yet -> execute immediately to avoid blank screen
        if not self._stack:
            action()
            self.log.info("Scene %s", kind, extra={"target": target})
            return

        if self.transitions and self.transition_spec_provider:
            if self.transitions.active:
                self.log.debug("Transition active; navigation skipped", extra={"kind": kind, "target": target})
                return
            spec = self.transition_spec_provider()
            if spec.duration > 0:
                self.transitions.start(spec, action)
                self.log.info("Scene %s (transition)", extra={"target": target, "kind": kind})
                return
        action()
        self.log.info("Scene %s", kind, extra={"target": target})

    def _push(self, name: str, payload: dict | None) -> None:
        if name not in self.scenes:
            raise KeyError(f"Scene '{name}' not registered")
        if self._stack:
            self.top.scene.on_exit({"next": name})
        item = _StackItem(name=name, scene=self.scenes[name], payload=payload)
        self._stack.append(item)
        item.scene.on_enter(payload)

    def _replace_stack_with(self, name: str, payload: dict | None) -> None:
        self._pop_all()
        self._push(name, payload)

    def _pop_all(self) -> None:
        while self._stack:
            item = self._stack.pop()
            item.scene.on_exit({"reason": "stack_clear"})

    @property
    def top(self) -> _StackItem:
        return self._stack[-1]

    @property
    def current_name(self) -> str | None:
        return self._stack[-1].name if self._stack else None

    @property
    def previous_name(self) -> str | None:
        if len(self._stack) >= 2:
            return self._stack[-2].name
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._stack:
            self.log.debug("Handle event", extra={"scene": self.current_name, "event": event.type})
            self.top.scene.handle_event(event)

    def handle_input(self, input_state) -> None:
        if self._stack:
            self.top.scene.handle_input(input_state)

    def handle_game_event(self, event) -> None:
        if self._stack and hasattr(self.top.scene, "on_event"):
            try:
                self.top.scene.on_event(event)
            except Exception:
                self.log.exception("Scene event handler failed", extra={"scene": self.current_name, "event": type(event).__name__})

    def update(self, dt: float) -> None:
        if self._stack:
            self.log.debug("Update scene", extra={"scene": self.current_name, "dt": dt})
            self.top.scene.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        if self._stack:
            self.top.scene.draw(screen)
