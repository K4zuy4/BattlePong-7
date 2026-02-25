from __future__ import annotations

"""Input abstraction: maps pygame key events to high-level actions."""

import pygame
from enum import Enum, auto
from typing import Dict, Set, Iterable, Tuple


class Action(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    CONFIRM = auto()
    BACK = auto()
    PAUSE = auto()
    MENU_UP = auto()
    MENU_DOWN = auto()


def default_keymap() -> Dict[int, Set[Action]]:
    return {
        pygame.K_w: {Action.UP, Action.MENU_UP},
        pygame.K_s: {Action.DOWN, Action.MENU_DOWN},
        pygame.K_UP: {Action.UP, Action.MENU_UP},
        pygame.K_DOWN: {Action.DOWN, Action.MENU_DOWN},
        pygame.K_RETURN: {Action.CONFIRM},
        pygame.K_SPACE: {Action.CONFIRM},
        pygame.K_ESCAPE: {Action.BACK, Action.PAUSE},
        pygame.K_p: {Action.PAUSE},
    }


def build_keymap_from_actions(action_to_key: Dict[str, int]) -> Dict[int, Set[Action]]:
    """Builds a key->actions mapping from an action->key config."""
    keymap: Dict[int, Set[Action]] = {}
    for name, key in action_to_key.items():
        try:
            action = Action[name]
        except KeyError:
            continue
        keymap.setdefault(key, set()).add(action)
        # mirror menu navigation
        if action == Action.UP:
            keymap.setdefault(key, set()).add(Action.MENU_UP)
        if action == Action.DOWN:
            keymap.setdefault(key, set()).add(Action.MENU_DOWN)
    return keymap


def serialize_keymap(keymap: Dict[str, int]) -> Dict[str, int]:
    return keymap


def default_action_keys() -> Dict[str, int]:
    return {
        "UP": pygame.K_w,
        "DOWN": pygame.K_s,
        "CONFIRM": pygame.K_RETURN,
        "BACK": pygame.K_ESCAPE,
        "PAUSE": pygame.K_p,
    }


def default_joymap() -> Dict[Tuple[int, int], Set[Action]]:
    """Map (control_type, id) -> actions.

    control_type: 0=button, 1=hat (only first axis up/down), 2=axis (not used here).
    """
    return {
        (0, 0): {Action.CONFIRM},  # A / Cross
        (0, 1): {Action.BACK},     # B / Circle
        (0, 7): {Action.PAUSE},    # Start/Options
        (1, 0): {Action.MENU_UP, Action.UP},    # hat up
        (1, 1): {Action.MENU_DOWN, Action.DOWN},# hat down
    }


class InputState:
    def __init__(
        self,
        keymap: Dict[int, Set[Action]] | None = None,
        joymap: Dict[Tuple[int, int], Set[Action]] | None = None,
        enable_joystick: bool = True,
    ) -> None:
        self.keymap = keymap or default_keymap()
        self.joymap = joymap or default_joymap()
        self.held: Set[Action] = set()
        self._pressed_once: Set[Action] = set()
        self.joysticks: list[pygame.joystick.Joystick] = []
        if enable_joystick:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                js = pygame.joystick.Joystick(i)
                js.init()
                self.joysticks.append(js)

    def process_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            actions = self.keymap.get(event.key, set())
            self._apply(actions, pressed=event.type == pygame.KEYDOWN)
        elif event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
            key = (0, event.button)
            actions = self.joymap.get(key, set())
            self._apply(actions, pressed=event.type == pygame.JOYBUTTONDOWN)
        elif event.type == pygame.JOYHATMOTION:
            # only primary hat
            hat_x, hat_y = event.value
            if hat_y == 1:
                self._apply(self.joymap.get((1, 0), set()), pressed=True)
            elif hat_y == -1:
                self._apply(self.joymap.get((1, 1), set()), pressed=True)
            else:
                self._apply({Action.MENU_UP, Action.MENU_DOWN, Action.UP, Action.DOWN}, pressed=False)

    def _apply(self, actions: Iterable[Action], pressed: bool) -> None:
        for act in actions:
            if pressed:
                if act not in self.held:
                    self._pressed_once.add(act)
                self.held.add(act)
            else:
                self.held.discard(act)

    def rebind_key(self, key: int, actions: Set[Action]) -> None:
        self.keymap[key] = actions

    def rebind_joy_button(self, button: int, actions: Set[Action]) -> None:
        self.joymap[(0, button)] = actions

    def is_held(self, action: Action) -> bool:
        return action in self.held

    def consume(self, action: Action) -> bool:
        """Return True once per keydown."""
        if action in self._pressed_once:
            self._pressed_once.discard(action)
            return True
        return False

    # Focus navigation helpers ------------------------------------------- #
    def nav_vertical(self) -> int:
        """Returns -1 (up), +1 (down) or 0 based on MENU actions; consumes once."""
        if self.consume(Action.MENU_UP):
            return -1
        if self.consume(Action.MENU_DOWN):
            return 1
        return 0

    def nav_horizontal(self) -> int:
        if self.consume(Action.LEFT):
            return -1
        if self.consume(Action.RIGHT):
            return 1
        return 0
