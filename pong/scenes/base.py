from __future__ import annotations

import pygame
import logging


class Scene:
    def handle_event(self, event: pygame.event.Event) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        raise NotImplementedError

    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass


class SceneManager:
    def __init__(self) -> None:
        self.scenes: dict[str, Scene] = {}
        self.current: str | None = None
        self._history: list[str] = []
        self.log = logging.getLogger(__name__)

    def register(self, name: str, scene: Scene) -> None:
        self.scenes[name] = scene
        self.log.debug("Scene registered", extra={"name": name})

    def set_scene(self, name: str) -> None:
        if self.current == name:
            return
        if self.current:
            self.scenes[self.current].on_exit()
            self._history.append(self.current)
        self.current = name
        self.scenes[name].on_enter()
        self.log.info("Scene change", extra={"current": self.current})

    def go_back(self) -> None:
        if not self._history:
            return
        prev = self._history.pop()
        if self.current:
            self.scenes[self.current].on_exit()
        self.current = prev
        self.scenes[self.current].on_enter()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.current:
            self.scenes[self.current].handle_event(event)

    def update(self, dt: float) -> None:
        if self.current:
            self.scenes[self.current].update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        if self.current:
            self.scenes[self.current].draw(screen)
