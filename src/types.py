"""Core data types for Stratagem."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json


class Terrain(str, Enum):
    PLAINS = "plains"
    MOUNTAINS = "mountains"
    FOREST = "forest"
    COAST = "coast"
    WASTELAND = "wasteland"


TERRAIN_DEFENSE_BONUS = {
    Terrain.PLAINS: 0,
    Terrain.MOUNTAINS: 2,
    Terrain.FOREST: 1,
    Terrain.COAST: 0,
    Terrain.WASTELAND: 0,
}

TERRAIN_RESOURCES = {
    Terrain.PLAINS: {"food": 3, "iron": 0, "gold": 1},
    Terrain.MOUNTAINS: {"food": 0, "iron": 3, "gold": 1},
    Terrain.FOREST: {"food": 2, "iron": 1, "gold": 0},
    Terrain.COAST: {"food": 2, "iron": 0, "gold": 2},
    Terrain.WASTELAND: {"food": 0, "iron": 2, "gold": 2},
}


class UnitType(str, Enum):
    MILITIA = "militia"
    SOLDIERS = "soldiers"
    KNIGHTS = "knights"
    SIEGE = "siege"
    SCOUT = "scout"
    SPY = "spy"


UNIT_STATS = {
    #                   cost(food,iron,gold)  strength  speed
    UnitType.MILITIA:   ({"food": 1}, 1, 1),
    UnitType.SOLDIERS:  ({"food": 1, "iron": 1}, 3, 1),
    UnitType.KNIGHTS:   ({"food": 1, "iron": 2, "gold": 1}, 5, 2),
    UnitType.SIEGE:     ({"iron": 2, "gold": 2}, 2, 1),
    UnitType.SCOUT:     ({"gold": 1}, 0, 3),
    UnitType.SPY:       ({"gold": 3}, 0, 2),
}


@dataclass
class Unit:
    id: str
    type: UnitType
    owner: str
    province: str

    @property
    def strength(self) -> int:
        return UNIT_STATS[self.type][1]

    @property
    def speed(self) -> int:
        return UNIT_STATS[self.type][2]


class BuildingType(str, Enum):
    FARM = "farm"
    MINE = "mine"
    MARKET = "market"
    FORTRESS = "fortress"
    BARRACKS = "barracks"
    WATCHTOWER = "watchtower"
    EMBASSY = "embassy"


@dataclass
class Building:
    type: BuildingType
    turns_remaining: int = 0  # 0 = complete


@dataclass
class Province:
    id: str
    name: str
    terrain: Terrain
    owner: Optional[str] = None
    units: list[Unit] = field(default_factory=list)
    buildings: list[Building] = field(default_factory=list)
    adjacent: list[str] = field(default_factory=list)

    @property
    def base_resources(self) -> dict[str, int]:
        return dict(TERRAIN_RESOURCES[self.terrain])

    @property
    def defense_bonus(self) -> int:
        bonus = TERRAIN_DEFENSE_BONUS[self.terrain]
        for b in self.buildings:
            if b.type == BuildingType.FORTRESS and b.turns_remaining == 0:
                bonus += 3
        return bonus

    def resource_production(self) -> dict[str, int]:
        prod = self.base_resources.copy()
        for b in self.buildings:
            if b.turns_remaining > 0:
                continue
            if b.type == BuildingType.FARM:
                prod["food"] = prod.get("food", 0) + 2
            elif b.type == BuildingType.MINE:
                prod["iron"] = prod.get("iron", 0) + 2
            elif b.type == BuildingType.MARKET:
                prod["gold"] = prod.get("gold", 0) + 1
        return prod


@dataclass
class Player:
    id: str
    name: str
    resources: dict[str, int] = field(default_factory=lambda: {"food": 10, "iron": 5, "gold": 5})
    alive: bool = True


@dataclass
class MoveOrder:
    unit_id: str
    target_province: str


@dataclass
class BuildUnitOrder:
    unit_type: UnitType
    province: str


@dataclass
class BuildBuildingOrder:
    building_type: BuildingType
    province: str


@dataclass
class Orders:
    player_id: str
    moves: list[MoveOrder] = field(default_factory=list)
    build_units: list[BuildUnitOrder] = field(default_factory=list)
    build_buildings: list[BuildBuildingOrder] = field(default_factory=list)


@dataclass
class CombatResult:
    province: str
    attackers: dict[str, int]  # player_id -> strength
    winner: str
    losses: dict[str, int]  # player_id -> units lost


@dataclass
class TurnResult:
    turn: int
    combats: list[CombatResult] = field(default_factory=list)
    resources_collected: dict[str, dict[str, int]] = field(default_factory=dict)
    eliminations: list[str] = field(default_factory=list)
    winner: Optional[str] = None
