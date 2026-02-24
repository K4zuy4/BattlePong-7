from __future__ import annotations

"""Tiny tween helpers and easing presets."""

import math
from typing import Callable


# Easing library ---------------------------------------------------------- #

def ease_linear(t: float) -> float:
    return t


def ease_out_cubic(t: float) -> float:
    return 1 - pow(1 - t, 3)


def ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2


def ease_out_back(t: float, s: float = 1.70158) -> float:
    return 1 + (s + 1) * pow(t - 1, 3) + s * pow(t - 1, 2)


def ease_out_elastic(t: float) -> float:
    if t == 0 or t == 1:
        return t
    c = (2 * math.pi) / 3
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c) + 1


PRESETS: dict[str, Callable[[float], float]] = {
    "linear": ease_linear,
    "out_cubic": ease_out_cubic,
    "in_out_quad": ease_in_out_quad,
    "out_back": ease_out_back,
    "out_elastic": ease_out_elastic,
}


def tween(progress: float, easing: str = "linear") -> float:
    p = max(0.0, min(1.0, progress))
    fn: Callable[[float], float] = PRESETS.get(easing, ease_linear)
    return fn(p)
