from __future__ import annotations

"""Tiny layout helpers for rows/columns with spacing and padding."""

from typing import Iterable, Tuple


def column(anchor: tuple[int, int], size: tuple[int, int], spacing: int, count: int) -> list[tuple[int, int]]:
    x, y = anchor
    w, h = size
    return [(x, y + i * (h + spacing)) for i in range(count)]


def row(anchor: tuple[int, int], size: tuple[int, int], spacing: int, count: int) -> list[tuple[int, int]]:
    x, y = anchor
    w, h = size
    return [(x + i * (w + spacing), y) for i in range(count)]


def grid(anchor: tuple[int, int], cell: tuple[int, int], cols: int, spacing: tuple[int, int], count: int) -> list[tuple[int, int]]:
    x0, y0 = anchor
    cw, ch = cell
    sx, sy = spacing
    positions = []
    for i in range(count):
        row_idx = i // cols
        col_idx = i % cols
        positions.append((x0 + col_idx * (cw + sx), y0 + row_idx * (ch + sy)))
    return positions
