from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AbilitySpec:
    id: str
    name: str
    description: str
    cooldown: float
    duration: float
    rarity: str = "core"


DEFAULT_ABILITY_ID = "goal_shield"


ABILITY_SPECS: dict[str, AbilitySpec] = {
    "paddle_dash": AbilitySpec(
        id="paddle_dash",
        name="Paddle Dash",
        description="Short burst movement in the current paddle direction.",
        cooldown=4.0,
        duration=0.18,
        rarity="rare",
    ),
    "speed_boost": AbilitySpec(
        id="speed_boost",
        name="Speed Boost",
        description="Temporarily increases paddle movement speed.",
        cooldown=7.5,
        duration=2.75,
        rarity="epic",
    ),
    "goal_shield": AbilitySpec(
        id="goal_shield",
        name="Goal Shield",
        description="Blocks your goal for a short time.",
        cooldown=9.0,
        duration=3.5,
        rarity="core",
    ),
}


def list_abilities() -> list[AbilitySpec]:
    return [ABILITY_SPECS[key] for key in sorted(ABILITY_SPECS.keys())]


def ability_inventory_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for spec in list_abilities():
        items.append(
            {
                "id": spec.id,
                "name": spec.name,
                "path": None,
                "price": 0,
                "rarity": spec.rarity,
                "description": spec.description,
                "cooldown": spec.cooldown,
                "duration": spec.duration,
            }
        )
    return items
