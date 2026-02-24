from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional

from .manifest import SkinManifest, load_manifest, ManifestError


class SkinRegistry:
    """Loads skin manifests from a directory and manages active skin."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.skins: Dict[str, SkinManifest] = {}
        self.active: Optional[str] = None
        self._listeners: list[Callable[[SkinManifest], None]] = []
        self.refresh()

    def refresh(self) -> None:
        self.skins.clear()
        if not self.root.exists():
            return
        for manifest_path in self.root.rglob("manifest.json"):
            try:
                manifest = load_manifest(manifest_path)
                self.skins[manifest.name] = manifest
            except ManifestError:
                continue

    def list(self) -> list[str]:
        return sorted(self.skins.keys())

    def on_change(self, listener: Callable[[SkinManifest], None]) -> None:
        self._listeners.append(listener)

    def apply(self, name: str) -> SkinManifest:
        if name not in self.skins:
            raise KeyError(f"skin '{name}' not found")
        manifest = self.skins[name]
        self.active = name
        for listener in self._listeners:
            listener(manifest)
        return manifest

    def current(self) -> Optional[SkinManifest]:
        if self.active and self.active in self.skins:
            return self.skins[self.active]
        return None
