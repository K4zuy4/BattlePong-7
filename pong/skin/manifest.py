from __future__ import annotations

"""Skin manifest schema and loader."""

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Optional


@dataclass
class Palette:
    primary: str = "#5B8CFF"
    accent: str = "#FFB86C"
    background: str = "#0E111A"
    foreground: str = "#E6E6E6"
    highlight: str = "#FFFFFF"


@dataclass
class TrailSpec:
    effect: str = "trail_none"
    color: Optional[str] = None


@dataclass
class AudioSpec:
    hit: Optional[str] = None
    score: Optional[str] = None
    ui: Optional[str] = None


@dataclass
class AnimationSpec:
    spawn: Optional[str] = None
    hit: Optional[str] = None
    goal: Optional[str] = None


@dataclass
class SkinManifest:
    name: str
    author: str | None = None
    version: str | None = None
    palette: Palette = field(default_factory=Palette)
    assets: dict[str, str] = field(default_factory=dict)  # e.g., {"ball": "ball.png", "paddle": "pad.png", "bg": "bg.png"}
    trail: TrailSpec = field(default_factory=TrailSpec)
    audio: AudioSpec = field(default_factory=AudioSpec)
    animation: AnimationSpec = field(default_factory=AnimationSpec)


class ManifestError(Exception):
    pass


def _hex_or_default(value: str | None, default: str) -> str:
    if not value or not isinstance(value, str):
        return default
    if not value.startswith("#") or len(value) not in (4, 7):
        raise ManifestError(f"Invalid color: {value}")
    return value


def load_manifest(path: Path) -> SkinManifest:
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        raise ManifestError(f"Failed to read manifest {path}: {exc}")

    if "name" not in data:
        raise ManifestError("manifest missing 'name'")

    palette_data = data.get("palette", {})
    palette = Palette(
        primary=_hex_or_default(palette_data.get("primary"), Palette.primary),
        accent=_hex_or_default(palette_data.get("accent"), Palette.accent),
        background=_hex_or_default(palette_data.get("background"), Palette.background),
        foreground=_hex_or_default(palette_data.get("foreground"), Palette.foreground),
        highlight=_hex_or_default(palette_data.get("highlight"), Palette.highlight),
    )

    manifest = SkinManifest(
        name=data["name"],
        author=data.get("author"),
        version=data.get("version"),
        palette=palette,
        assets=data.get("assets", {}),
        trail=TrailSpec(**data.get("trail", {})),
        audio=AudioSpec(**data.get("audio", {})),
        animation=AnimationSpec(**data.get("animation", {})),
    )
    return manifest
