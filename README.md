# Battle Pong (PyGame)

Jetzt als Event-getriebenes Sandbox-Pong, in dem wirklich jede Zahl zur Laufzeit
angepasst werden kann (Speed, Größe, Ballanzahl, etc.).

- **RuntimeSettings** (`pong/settings.py`) hält alle Werte mutierbar.
- **Events** (`pong/events.py`) für Setting-Patches, Ball-Spawns, Scores, Resets.
- **Systems** (`pong/systems.py`) demonstriert Live-Manipulation (ChaosSystem).
- **PowerupManager** (`pong/powerups.py`) bleibt schlank und event-basiert.
- **Skins & Particles** (`pong/skins.py`, `pong/particles.py`) für Sprites/Rotation und Effekte.
- **Scene/UX** (`pong/app.py`, `pong/scenes.py`, `pong/ui/widgets.py`) für Menüs (Title, Mode Select, Play, Pause, Inventory, Shop, Settings).

## Start

```bash
python3 -m pip install pygame
python3 main.py
```

## Erweitern (quick path)

1. Events definieren (`pong/events.py`), z. B. `SettingsChangeRequested`.
2. System oder Powerup schreiben, das sich auf die Events subscribed.
3. Optional: eigene Settings-Patches per `bus.publish(SettingsChangeRequested(...))`.
4. Balls on demand: `bus.publish(SpawnBallRequested(count=3, speed=500))`.

## Controls

- Links: `W/S`
- Rechts: `Pfeil hoch/runter`
- Nach Spielende: `R` für Restart
- `Space`: einen weiteren Ball spawnen
- Optional: Hintergründe/Tiles und Sprites können über Settings gewechselt werden (siehe unten).

## Live-Tweaks & Beispiele

- **Ball-Speed/Size ändern:** `bus.publish(SettingsChangeRequested(section="ball", values={"speed": 480, "size": 12}))`
- **Display umschalten:** `bus.publish(SettingsChangeRequested(section="display", values={"width": 1280, "height": 720}))`
  (Screen wird sofort neu erstellt.)
- **ChaosSystem** (standardmäßig aktiv) zeigt, wie Systeme per EventBus Werte umschreiben und neue Bälle spawnen.
- **Skins setzen:** `bus.publish(SettingsChangeRequested(section="sprites", values={"ball_image": "assets/ball.png", "paddle_image": "assets/paddle.png", "background_image": "assets/bg.png", "ball_rotation_speed": 120}))`
  oder lege Dateien in `skins/ball|paddle|background/` ab und trage den Pfad entsprechend ein (z. B. `skins/ball/ball_fire.png`).

## Skins-Ordner

- `skins/ball/` – PNGs für Bälle (werden kreisförmig maskiert & skaliert), README beschreibt Format.
- `skins/paddle/` – PNGs für Paddles (werden skaliert).
- `skins/background/` – PNG/JPG für Hintergründe (skaliert oder gekachelt).
- `skins/trail/` – Platzhalter für künftige Trail-/Animation-Assets.

## Dateien

- `pong/game.py` – Game-Loop, Event-Wiring, Multi-Ball-Handling, UI.
- `pong/settings.py` – zentrale RuntimeSettings, patchbar zur Laufzeit.
- `pong/events.py` – domänenspezifische Events inkl. Settings-/Spawn-Requests.
- `pong/systems.py` – Beispielsysteme (Chaos).
- `pong/entities.py` – Paddles & Balls lesen immer aktuelle Settings.
- `pong/app.py`, `pong/scenes.py`, `pong/ui/widgets.py` – SceneManager + Menüs (Title, Play, Inventory, Shop, Settings, Pause).
