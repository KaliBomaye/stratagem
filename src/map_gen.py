"""Map generation for Stratagem v2 — fixed tournament map with geographic structure."""
from __future__ import annotations
from .types import Province, Terrain, Unit, UnitType

# ── Tournament Map Definition ────────────────────────────────────────────────
# 24 provinces arranged in a symmetric 4-player layout.
# Coordinates are on a 0-1000 grid for frontend rendering.
#
# Layout concept:
#   4 corners = player home regions (2 provinces each)
#   4 frontier zones between adjacent players
#   4 center provinces = high-value contested territory
#
# Symmetry: 4-fold rotational symmetry around center.

TOURNAMENT_MAP = [
    # id, name, terrain, x, y
    # ── NW Home (Player 0) ──
    ("frostgate",   "Frostgate",    Terrain.MOUNTAIN, 120, 100),
    ("snowhaven",   "Snowhaven",    Terrain.PLAINS,    80, 230),
    # ── NE Home (Player 1) ──
    ("stormwatch",  "Stormwatch",   Terrain.MOUNTAIN, 880, 100),
    ("windcrest",   "Windcrest",    Terrain.PLAINS,   920, 230),
    # ── SW Home (Player 2) ──
    ("moonhaven",   "Moonhaven",    Terrain.MOUNTAIN, 120, 900),
    ("silverlake",  "Silverlake",   Terrain.PLAINS,    80, 770),
    # ── SE Home (Player 3) ──
    ("fireridge",   "Fireridge",    Terrain.MOUNTAIN, 880, 900),
    ("emberveil",   "Emberveil",    Terrain.PLAINS,   920, 770),
    # ── North Frontier ──
    ("crystalpeak", "Crystalpeak",  Terrain.COAST,    500,  80),
    ("thornfield",  "Thornfield",   Terrain.FOREST,   330, 180),
    ("ironridge",   "Ironridge",    Terrain.RIVER,    670, 180),
    # ── South Frontier ──
    ("darkhollow",  "Darkhollow",   Terrain.COAST,    500, 920),
    ("ashford",     "Ashford",      Terrain.FOREST,   330, 820),
    ("stonekeep",   "Stonekeep",    Terrain.RIVER,    670, 820),
    # ── West Frontier ──
    ("mistwood",    "Mistwood",     Terrain.FOREST,    60, 500),
    ("deepwood",    "Deepwood",     Terrain.RIVER,    200, 420),
    ("oakmere",     "Oakmere",      Terrain.RIVER,    200, 580),
    # ── East Frontier ──
    ("sunharbor",   "Sunharbor",    Terrain.COAST,    940, 500),
    ("goldreach",   "Goldreach",    Terrain.RIVER,    800, 420),
    ("coralcove",   "Coralcove",    Terrain.RIVER,    800, 580),
    # ── Center (high value) ──
    ("kingscross",  "King's Cross", Terrain.PLAINS,   500, 380),
    ("dragonseat",  "Dragon's Seat",Terrain.MOUNTAIN, 500, 620),
    ("tradeway",    "Tradeway",     Terrain.COAST,    380, 500),
    ("highmarket",  "Highmarket",   Terrain.COAST,    620, 500),
]

# Adjacency list (bidirectional — only list each edge once)
TOURNAMENT_EDGES = [
    # NW home connections
    ("frostgate", "snowhaven"), ("frostgate", "thornfield"), ("frostgate", "crystalpeak"),
    ("snowhaven", "thornfield"), ("snowhaven", "deepwood"), ("snowhaven", "mistwood"),
    # NE home connections
    ("stormwatch", "windcrest"), ("stormwatch", "ironridge"), ("stormwatch", "crystalpeak"),
    ("windcrest", "ironridge"), ("windcrest", "goldreach"), ("windcrest", "sunharbor"),
    # SW home connections
    ("moonhaven", "silverlake"), ("moonhaven", "ashford"), ("moonhaven", "darkhollow"),
    ("silverlake", "ashford"), ("silverlake", "oakmere"), ("silverlake", "mistwood"),
    # SE home connections
    ("fireridge", "emberveil"), ("fireridge", "stonekeep"), ("fireridge", "darkhollow"),
    ("emberveil", "stonekeep"), ("emberveil", "coralcove"), ("emberveil", "sunharbor"),
    # North frontier
    ("crystalpeak", "thornfield"), ("crystalpeak", "ironridge"),
    ("thornfield", "deepwood"), ("thornfield", "kingscross"),
    ("ironridge", "goldreach"), ("ironridge", "kingscross"),
    # South frontier
    ("darkhollow", "ashford"), ("darkhollow", "stonekeep"),
    ("ashford", "oakmere"), ("ashford", "dragonseat"),
    ("stonekeep", "coralcove"), ("stonekeep", "dragonseat"),
    # West frontier
    ("mistwood", "deepwood"), ("mistwood", "oakmere"),
    ("deepwood", "tradeway"), ("deepwood", "kingscross"),
    ("oakmere", "tradeway"), ("oakmere", "dragonseat"),
    # East frontier
    ("sunharbor", "goldreach"), ("sunharbor", "coralcove"),
    ("goldreach", "highmarket"), ("goldreach", "kingscross"),
    ("coralcove", "highmarket"), ("coralcove", "dragonseat"),
    # Center connections
    ("kingscross", "tradeway"), ("kingscross", "highmarket"),
    ("dragonseat", "tradeway"), ("dragonseat", "highmarket"),
    ("tradeway", "highmarket"),
]

# Starting provinces per player slot
PLAYER_STARTS = [
    ["frostgate", "snowhaven"],      # Player 0 (NW)
    ["stormwatch", "windcrest"],      # Player 1 (NE)
    ["moonhaven", "silverlake"],      # Player 2 (SW)
    ["fireridge", "emberveil"],       # Player 3 (SE)
]

CIVS = ["ironborn", "verdanti", "tidecallers", "ashwalkers"]


def generate_map(num_players: int = 4, seed: int | None = None) -> dict[str, Province]:
    """Generate the tournament map. num_players must be 2 or 4."""
    provinces: dict[str, Province] = {}

    for pid, name, terrain, x, y in TOURNAMENT_MAP:
        provinces[pid] = Province(id=pid, name=name, terrain=terrain, x=x, y=y)

    # Build adjacency
    for a, b in TOURNAMENT_EDGES:
        if b not in provinces[a].adjacent:
            provinces[a].adjacent.append(b)
        if a not in provinces[b].adjacent:
            provinces[b].adjacent.append(a)

    # Assign starting provinces and units
    active_starts = PLAYER_STARTS[:num_players]
    for i, start_provs in enumerate(active_starts):
        player_id = f"p{i}"
        for j, spid in enumerate(start_provs):
            prov = provinces[spid]
            prov.owner = player_id
            if j == 0:
                # Capital province: militia + infantry + scout
                prov.units = [
                    Unit(id=f"{player_id}_mil_0", type=UnitType.MILITIA, owner=player_id, province=spid),
                    Unit(id=f"{player_id}_inf_0", type=UnitType.INFANTRY, owner=player_id, province=spid),
                    Unit(id=f"{player_id}_sco_0", type=UnitType.SCOUT, owner=player_id, province=spid),
                ]
            else:
                # Second province: militia
                prov.units = [
                    Unit(id=f"{player_id}_mil_1", type=UnitType.MILITIA, owner=player_id, province=spid),
                ]

    return provinces
