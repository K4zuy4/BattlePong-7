# Battle Pong Template (PyGame)

Eine saubere Pong-Vorlage mit Fokus auf Erweiterbarkeit:

- **EventBus** (`pong/events.py`) für lose gekoppelte Gameplay-Features.
- **PowerupManager** (`pong/powerups.py`) als Einstieg für neue Effekte.
- **Klar getrennte Module** für Config, Entitäten, Game-Loop und Systeme.

## Start

```bash
python3 -m pip install pygame
python3 main.py
```

## Erweitern

1. Neue Event-Klasse in `pong/events.py` erstellen.
2. Neues System/Powerup schreiben (z. B. in `pong/powerups.py`) und auf Events subscriben.
3. Im `PongGame` nur noch zusammensetzen – keine harte Kopplung.

## Controls

- Links: `W/S`
- Rechts: `Pfeil hoch/runter`
- Nach Spielende: `R` für Restart
