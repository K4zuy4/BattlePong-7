# Battle Pong (PyGame) – Rebuilt Backbone

Aktueller Zustand: Minimal-Gameplay-Stub mit Szene-Stack, Transitions, Skin-System, Satire-Shop/Credits, Theme-aware UI.

## Start

```bash
python3 -m pip install pygame
python3 main.py
```

## Features (Stand now)

- Scene-Stack mit Fade-Transitions (Title, Play, Pause, Settings, Skins, Shop).
- Skin-System mit Paletten, optionalem Hintergrundbild; Wechsel via F6 oder Skins-Szene.
- Credits/Wallet & Owned-Skins persistent (`data/wallet.json`, `data/skins_owned.json`); Satire-Shop vergibt Credits, Skins können gekauft und angewendet werden.
- Theme Tokens: UI-Farben passen sich der aktiven Skin-Palette an.
- Input: Tastatur + Gamepad (Buttons/Hat), Focus-Navigation; ESC/PAUSE kontextsensitiv (Play↔Pause, Settings zurück nach Pause/Title).
- Debug-Overlay (FPS, Scene, Transition, Skin, Credits, in_game) – immer sichtbar.
- Headless-Fallback: wenn kein Video-Device verfügbar ist, nutzt SDL den Dummy-Treiber (Fensterlos), damit das Programm nicht hängen bleibt.
- Audio entfernt (Stand jetzt), um Hänger zu vermeiden.

## Steuerung (aktuell)

- Pfeiltasten / W-S zur Menü-Navigation, Enter/Space bestätigt.
- ESC/PAUSE: in Play Pause toggeln, in Settings zurück, sonst zum Title (abhängig vom Stack).
- F5/F6: Skins neu einlesen / durch Skins rotieren.

## Ökonomie (Satire)

- Shop-Szene bietet Credit-Packs (1000C, 5000C) „für 9.999€ / 49.999€“ – Klick vergibt Credits sofort.
- Skins kosten 1000C (basic) oder 2000C (premium); Kauf schaltet Skin frei, Apply setzt Palette/Assets.

## Dateien & Pfade

- `data/wallet.json`, `data/skins_owned.json` – Persistenz für Credits und Besitz.
- `skins/<pack>/manifest.json` – Paletten/Assets für Skins.
- `pong/app.py` – App Loop, SceneManager, Theme/Skin/Wallet-Handling.
- `pong/scenes/` – Title/Play/Pause/Settings/Skins/Shop.
- `pong/ui/` – Widgets, Theme, Layout, Focus, Tween.
- `pong/skin/` – Manifest-Schema + Registry.

## Was noch fehlt / Next Steps (geplant)

- Gameplay-Core (Ball/Paddle, Physik) neu anbinden an Skin-Assets.
- Tests (SceneManager, Manifest, Input/Focus).
