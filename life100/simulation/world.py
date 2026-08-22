"""World data model and deterministic procedural world generation.

SRS §7. World generation must be deterministic: the same seed + config must
always produce an identical World. No unseeded randomness is used anywhere
in this module (CLAUDE.md ground rule 8) — a `random.Random(seed)` is
constructed locally and never leaks out.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

ZONE_KINDS = ("residential", "commercial", "industrial", "park", "road")
BUILDING_KINDS = (
    "home",
    "school",
    "hospital",
    "shop",
    "factory",
    "bank",
    "government",
)


@dataclass(frozen=True)
class WorldConfig:
    """Configuration used to procedurally generate a World.

    Two World objects generated from the same seed + config must be equal.
    """

    seed: int
    width: int = 40
    height: int = 40
    residential_ratio: float = 0.45
    commercial_ratio: float = 0.20
    industrial_ratio: float = 0.10
    park_ratio: float = 0.10
    # remainder of cells become roads

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("World dimensions must be positive")
        used = self.residential_ratio + self.commercial_ratio + self.industrial_ratio + self.park_ratio
        if not (0.0 < used <= 1.0):
            raise ValueError("Zone ratios must sum to a value in (0, 1]")


@dataclass(frozen=True)
class Zone:
    zone_id: str
    kind: str
    x: int
    y: int


@dataclass(frozen=True)
class Building:
    building_id: str
    kind: str
    x: int
    y: int


@dataclass(frozen=True)
class World:
    seed: int
    config: WorldConfig
    city_id: str
    zones: tuple[Zone, ...] = field(default_factory=tuple)
    buildings: tuple[Building, ...] = field(default_factory=tuple)

    def buildings_of_kind(self, kind: str) -> tuple[Building, ...]:
        return tuple(b for b in self.buildings if b.kind == kind)


def _zone_kind_for_roll(config: WorldConfig, roll: float) -> str:
    cumulative = 0.0
    for kind, ratio in (
        ("residential", config.residential_ratio),
        ("commercial", config.commercial_ratio),
        ("industrial", config.industrial_ratio),
        ("park", config.park_ratio),
    ):
        cumulative += ratio
        if roll < cumulative:
            return kind
    return "road"


def generate_world(config: WorldConfig, city_id: str = "city_001") -> World:
    """Deterministically generate a world from `config`.

    Same seed + config -> identical World (assert-able with `==`, since every
    field is a frozen dataclass / tuple of frozen dataclasses).
    """
    rng = random.Random(config.seed)

    zones: list[Zone] = []
    # Row-major scan order — fixed regardless of platform/hash seed, so the
    # sequence of rng draws (and therefore the output) is fully determined
    # by `config.seed`.
    for y in range(config.height):
        for x in range(config.width):
            roll = rng.random()
            kind = _zone_kind_for_roll(config, roll)
            zones.append(Zone(zone_id=f"zone_{x}_{y}", kind=kind, x=x, y=y))

    buildings: list[Building] = []
    building_counter = 0

    def next_building_id() -> str:
        nonlocal building_counter
        building_counter += 1
        return f"bld_{building_counter:04d}"

    residential = [z for z in zones if z.kind == "residential"]
    commercial = [z for z in zones if z.kind == "commercial"]
    industrial = [z for z in zones if z.kind == "industrial"]

    # Fixed single-instance civic infrastructure, deterministically placed at
    # the front of the residential/commercial pools (already in fixed scan
    # order, so this is reproducible).
    civic_plan = [
        ("hospital", residential, 1),
        ("school", residential, 2),
        ("government", commercial, 1),
        ("bank", commercial, 2),
    ]
    used_residential = 0
    used_commercial = 0
    for kind, pool, count in civic_plan:
        offset = used_residential if pool is residential else used_commercial
        for i in range(count):
            zone = pool[offset + i]
            buildings.append(Building(building_id=next_building_id(), kind=kind, x=zone.x, y=zone.y))
        if pool is residential:
            used_residential += count
        else:
            used_commercial += count

    # Remaining residential zones become homes.
    for zone in residential[used_residential:]:
        buildings.append(Building(building_id=next_building_id(), kind="home", x=zone.x, y=zone.y))

    # Remaining commercial zones become shops.
    for zone in commercial[used_commercial:]:
        buildings.append(Building(building_id=next_building_id(), kind="shop", x=zone.x, y=zone.y))

    # Industrial zones become factories.
    for zone in industrial:
        buildings.append(Building(building_id=next_building_id(), kind="factory", x=zone.x, y=zone.y))

    return World(
        seed=config.seed,
        config=config,
        city_id=city_id,
        zones=tuple(zones),
        buildings=tuple(buildings),
    )
