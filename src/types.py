"""Core data types for Stratagem v2."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Enums ────────────────────────────────────────────────────────────────────

class Terrain(str, Enum):
    PLAINS = "plains"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    COAST = "coast"
    RIVER = "river"

TERRAIN_SHORT = {
    Terrain.PLAINS: "P", Terrain.FOREST: "F", Terrain.MOUNTAIN: "M",
    Terrain.COAST: "C", Terrain.RIVER: "R",
}

TERRAIN_DEFENSE = {
    Terrain.PLAINS: 0, Terrain.FOREST: 1, Terrain.MOUNTAIN: 3,
    Terrain.COAST: 0, Terrain.RIVER: 1,
}

TERRAIN_RESOURCES = {
    Terrain.PLAINS:   (3, 0, 1),  # (food, iron, gold)
    Terrain.FOREST:   (2, 1, 0),
    Terrain.MOUNTAIN: (0, 3, 1),
    Terrain.COAST:    (2, 0, 2),
    Terrain.RIVER:    (2, 1, 1),
}


class UnitType(str, Enum):
    MILITIA = "militia"
    INFANTRY = "infantry"
    ARCHERS = "archers"
    CAVALRY = "cavalry"
    SIEGE = "siege"
    KNIGHTS = "knights"
    SCOUT = "scout"

# Order matters for compact array representation
UNIT_ORDER = [UnitType.MILITIA, UnitType.INFANTRY, UnitType.ARCHERS,
              UnitType.CAVALRY, UnitType.SIEGE, UnitType.KNIGHTS, UnitType.SCOUT]

# cost (food, iron, gold), base_strength, speed, min_age
UNIT_STATS: dict[UnitType, tuple[tuple[int,int,int], int, int, int]] = {
    UnitType.MILITIA:   ((1,0,0), 1, 1, 1),
    UnitType.INFANTRY:  ((1,1,0), 3, 1, 1),
    UnitType.ARCHERS:   ((1,0,1), 2, 1, 2),
    UnitType.CAVALRY:   ((2,1,0), 3, 2, 2),
    UnitType.SIEGE:     ((0,2,2), 1, 1, 3),
    UnitType.KNIGHTS:   ((2,2,1), 5, 2, 3),
    UnitType.SCOUT:     ((0,0,1), 0, 3, 1),
}

# Triangle bonuses: attacker type -> defender type -> bonus
TRIANGLE = {
    UnitType.INFANTRY: {UnitType.CAVALRY: 2},
    UnitType.ARCHERS:  {UnitType.INFANTRY: 2},
    UnitType.CAVALRY:  {UnitType.ARCHERS: 2},
}

# Terrain combat bonuses for unit types
TERRAIN_UNIT_BONUS = {
    UnitType.CAVALRY: {Terrain.PLAINS: 1},
    UnitType.ARCHERS: {Terrain.FOREST: 1},
}

# Unique units per civ (same format as UNIT_STATS entry)
UNIQUE_UNITS = {
    "ironborn":    ("huscarl",    (1,2,0), 6, 1, 2),  # name, cost, str, spd, min_age
    "verdanti":    ("herbalist",  (2,0,1), 1, 1, 2),
    "tidecallers": ("corsair",    (1,1,1), 3, 2, 2),
    "ashwalkers":  ("sage",       (1,0,2), 1, 1, 2),
}


class BuildingType(str, Enum):
    FARM = "farm"
    MINE = "mine"
    MARKET = "market"
    BARRACKS = "barracks"
    FORTRESS = "fortress"
    TRADE_POST = "trade_post"
    WATCHTOWER = "watchtower"

BUILDING_SHORT = {
    BuildingType.FARM: "F", BuildingType.MINE: "M", BuildingType.MARKET: "K",
    BuildingType.BARRACKS: "B", BuildingType.FORTRESS: "X",
    BuildingType.TRADE_POST: "T", BuildingType.WATCHTOWER: "W",
}

# cost (food, iron, gold), min_age
BUILDING_STATS: dict[BuildingType, tuple[tuple[int,int,int], int]] = {
    BuildingType.FARM:       ((2,0,0), 1),
    BuildingType.MINE:       ((0,2,0), 1),
    BuildingType.MARKET:     ((0,0,3), 1),
    BuildingType.BARRACKS:   ((0,2,0), 1),
    BuildingType.FORTRESS:   ((0,3,2), 2),
    BuildingType.TRADE_POST: ((0,0,2), 2),
    BuildingType.WATCHTOWER: ((0,1,1), 2),
}


class TechId(str, Enum):
    # Bronze age
    AGRICULTURE = "agr"
    MINING = "min"
    MASONRY = "mas"
    # Iron age
    TACTICS = "tac"
    COMMERCE = "com"
    FORTIFICATION = "for"
    # Steel age
    BLITZ = "bli"
    SIEGE_CRAFT = "sie"
    DIPLOMACY_TECH = "dip"

TECH_AGE = {
    TechId.AGRICULTURE: 1, TechId.MINING: 1, TechId.MASONRY: 1,
    TechId.TACTICS: 2, TechId.COMMERCE: 2, TechId.FORTIFICATION: 2,
    TechId.BLITZ: 3, TechId.SIEGE_CRAFT: 3, TechId.DIPLOMACY_TECH: 3,
}

# Techs in same age are mutually exclusive (pick one per age)
TECH_GROUPS = {1: [TechId.AGRICULTURE, TechId.MINING, TechId.MASONRY],
               2: [TechId.TACTICS, TechId.COMMERCE, TechId.FORTIFICATION],
               3: [TechId.BLITZ, TechId.SIEGE_CRAFT, TechId.DIPLOMACY_TECH]}

# Tech costs (food, iron, gold)
TECH_COST = {
    TechId.AGRICULTURE: (3,0,2), TechId.MINING: (0,3,2), TechId.MASONRY: (2,2,1),
    TechId.TACTICS: (3,3,2), TechId.COMMERCE: (2,0,5), TechId.FORTIFICATION: (2,4,2),
    TechId.BLITZ: (5,5,3), TechId.SIEGE_CRAFT: (3,6,3), TechId.DIPLOMACY_TECH: (3,3,6),
}

# Age advancement costs (food, iron, gold)
AGE_COST = {2: (10, 8, 5), 3: (15, 12, 10)}


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class Unit:
    id: str
    type: UnitType
    owner: str
    province: str
    veteran: int = 0  # +0 to +2 bonus strength

    @property
    def base_strength(self) -> int:
        return UNIT_STATS[self.type][1]

    @property
    def strength(self) -> int:
        return self.base_strength + self.veteran

    @property
    def speed(self) -> int:
        return UNIT_STATS[self.type][2]


@dataclass
class Building:
    type: BuildingType
    done: bool = True


@dataclass
class Province:
    id: str
    name: str
    terrain: Terrain
    x: float  # map position for frontend
    y: float
    owner: Optional[str] = None
    units: list[Unit] = field(default_factory=list)
    buildings: list[Building] = field(default_factory=list)
    adjacent: list[str] = field(default_factory=list)

    @property
    def base_resources(self) -> tuple[int, int, int]:
        return TERRAIN_RESOURCES[self.terrain]

    @property
    def defense_bonus(self) -> int:
        bonus = TERRAIN_DEFENSE[self.terrain]
        for b in self.buildings:
            if b.type == BuildingType.FORTRESS and b.done:
                bonus += 3
        return bonus

    def production(self, player_techs: list[TechId] | None = None) -> tuple[int, int, int]:
        """Returns (food, iron, gold) production."""
        f, i, g = self.base_resources
        for b in self.buildings:
            if not b.done:
                continue
            if b.type == BuildingType.FARM:
                f += 2
            elif b.type == BuildingType.MINE:
                i += 2
            elif b.type == BuildingType.MARKET:
                g += 2
        if player_techs:
            if TechId.AGRICULTURE in player_techs:
                # +1 food from farms
                for b in self.buildings:
                    if b.type == BuildingType.FARM and b.done:
                        f += 1
            if TechId.MINING in player_techs:
                for b in self.buildings:
                    if b.type == BuildingType.MINE and b.done:
                        i += 1
            if TechId.COMMERCE in player_techs:
                for b in self.buildings:
                    if b.type == BuildingType.MARKET and b.done:
                        g += 2
        return (f, i, g)

    def has_building(self, bt: BuildingType) -> bool:
        return any(b.type == bt and b.done for b in self.buildings)

    def unit_counts(self) -> list[int]:
        """Return unit counts in UNIT_ORDER for compact representation."""
        counts = [0] * len(UNIT_ORDER)
        for u in self.units:
            if u.type in UNIT_ORDER:
                counts[UNIT_ORDER.index(u.type)] += 1
        return counts


@dataclass
class TradeRoute:
    id: str
    from_province: str
    to_province: str
    owner: str  # player who created it
    partner: Optional[str] = None  # allied partner if shared route
    income: int = 0  # calculated each turn


@dataclass
class Player:
    id: str
    name: str
    civ: str = "ironborn"
    age: int = 1  # 1=Bronze, 2=Iron, 3=Steel
    resources: list[int] = field(default_factory=lambda: [10, 5, 5])  # [food, iron, gold]
    techs: list[TechId] = field(default_factory=list)
    alive: bool = True
    score: int = 0

    @property
    def food(self) -> int: return self.resources[0]
    @property
    def iron(self) -> int: return self.resources[1]
    @property
    def gold(self) -> int: return self.resources[2]

    def can_afford(self, cost: tuple[int,int,int]) -> bool:
        return self.resources[0] >= cost[0] and self.resources[1] >= cost[1] and self.resources[2] >= cost[2]

    def pay(self, cost: tuple[int,int,int]):
        self.resources[0] -= cost[0]
        self.resources[1] -= cost[1]
        self.resources[2] -= cost[2]

    def civ_unit_discount(self, cost: tuple[int,int,int]) -> tuple[int,int,int]:
        """Apply civ-specific cost reduction."""
        f, i, g = cost
        if self.civ == "ironborn":
            i = max(0, i - 1)
        return (f, i, g)

    def civ_tech_discount(self, cost: tuple[int,int,int]) -> tuple[int,int,int]:
        if self.civ == "ashwalkers":
            return (cost[0] * 3 // 4, cost[1] * 3 // 4, cost[2] * 3 // 4)
        return cost


# ── Orders ───────────────────────────────────────────────────────────────────

@dataclass
class MoveOrder:
    unit_id: str
    target: str  # province id

@dataclass
class BuildUnitOrder:
    unit_type: str  # UnitType value or "unique"
    province: str

@dataclass
class BuildBuildingOrder:
    building_type: str
    province: str

@dataclass
class ResearchOrder:
    tech: str  # TechId value or "age_up"

@dataclass
class TradeRouteOrder:
    from_province: str
    to_province: str

@dataclass
class Orders:
    player_id: str
    moves: list[MoveOrder] = field(default_factory=list)
    build_units: list[BuildUnitOrder] = field(default_factory=list)
    build_buildings: list[BuildBuildingOrder] = field(default_factory=list)
    research: Optional[ResearchOrder] = None
    trade_routes: list[TradeRouteOrder] = field(default_factory=list)
    diplomacy: Optional[DiplomacyOrder] = None


# ── Results ──────────────────────────────────────────────────────────────────

# ── Diplomacy ────────────────────────────────────────────────────────────────

class TreatyType(str, Enum):
    ALLIANCE = "alliance"
    TRADE = "trade"
    NON_AGGRESSION = "nap"
    CEASEFIRE = "ceasefire"

@dataclass
class DiplomacyMessage:
    sender: str
    recipient: str  # player_id or "public"
    content: str
    turn: int
    is_public: bool = False

@dataclass
class TreatyProposal:
    id: str
    proposer: str
    target: str
    treaty_type: TreatyType
    turn_proposed: int
    accepted: bool = False
    rejected: bool = False

@dataclass
class Treaty:
    id: str
    type: TreatyType
    parties: list[str]  # 2 player_ids
    turn_created: int
    broken_by: Optional[str] = None
    turn_broken: Optional[int] = None

    @property
    def active(self) -> bool:
        return self.broken_by is None

@dataclass
class DiplomacyOrder:
    messages: list[dict] = field(default_factory=list)  # [{to, content}]
    proposals: list[dict] = field(default_factory=list)  # [{target, type}]
    accept_treaties: list[str] = field(default_factory=list)  # treaty proposal ids
    reject_treaties: list[str] = field(default_factory=list)
    break_treaties: list[str] = field(default_factory=list)  # treaty ids to break


# ── Results ──────────────────────────────────────────────────────────────────

@dataclass
class CombatResult:
    province: str
    sides: dict[str, int]  # player_id -> total strength
    winner: str
    losses: dict[str, int]  # player_id -> units lost

@dataclass
class TurnResult:
    turn: int
    combats: list[CombatResult] = field(default_factory=list)
    income: dict[str, list[int]] = field(default_factory=dict)  # pid -> [f,i,g]
    eliminations: list[str] = field(default_factory=list)
    winner: Optional[str] = None
    events: list[str] = field(default_factory=list)  # text log entries
