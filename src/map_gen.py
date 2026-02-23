"""Procedural map generation for Stratagem."""
import random
from .types import Province, Terrain, Unit, UnitType

# Province name pools
PROVINCE_NAMES = [
    "Ironvale", "Thornfield", "Sunharbor", "Crystalpeak", "Darkhollow",
    "Mistwood", "Goldreach", "Stonekeep", "Ashford", "Deepwater",
    "Windcrest", "Shadowfen", "Brightmoor", "Frostgate", "Emberveil",
    "Silverlake", "Duskmeadow", "Stormwatch", "Greendale", "Bonemarsh",
    "Copperhill", "Ravenrock", "Starfall", "Willowbend", "Fireridge",
    "Moonhaven", "Driftwood", "Ironspire", "Thornhaven", "Cloudpeak",
    "Redmarsh", "Bluehaven", "Sandstone", "Nightfall", "Dawncrest",
    "Oakhold", "Serpentine", "Highwatch", "Lowmere", "Grimstone",
]


def generate_map(num_provinces: int = 25, num_players: int = 4, seed: int | None = None) -> dict[str, Province]:
    """Generate a connected graph of provinces."""
    rng = random.Random(seed)
    
    names = rng.sample(PROVINCE_NAMES, min(num_provinces, len(PROVINCE_NAMES)))
    terrains = list(Terrain)
    
    provinces: dict[str, Province] = {}
    for i, name in enumerate(names):
        pid = name.lower().replace(" ", "")
        terrain = rng.choice(terrains)
        provinces[pid] = Province(
            id=pid,
            name=name,
            terrain=terrain,
        )
    
    # Create connected graph using a spanning tree + random edges
    pids = list(provinces.keys())
    rng.shuffle(pids)
    
    # Spanning tree ensures connectivity
    for i in range(1, len(pids)):
        target = rng.randint(0, i - 1)
        provinces[pids[i]].adjacent.append(pids[target])
        provinces[pids[target]].adjacent.append(pids[i])
    
    # Add random extra edges for interesting topology (avg ~3 connections per node)
    extra_edges = num_provinces  # roughly doubles connections
    for _ in range(extra_edges):
        a, b = rng.sample(pids, 2)
        if b not in provinces[a].adjacent:
            provinces[a].adjacent.append(b)
            provinces[b].adjacent.append(a)
    
    # Assign starting provinces to players
    # Pick spread-out starting positions
    starts = pids[:num_players]  # simplified — first N after shuffle
    
    for i, start_pid in enumerate(starts):
        player_id = f"player_{i}"
        prov = provinces[start_pid]
        prov.owner = player_id
        # Starting units
        prov.units = [
            Unit(id=f"{player_id}_militia_0", type=UnitType.MILITIA, owner=player_id, province=start_pid),
            Unit(id=f"{player_id}_soldiers_0", type=UnitType.SOLDIERS, owner=player_id, province=start_pid),
            Unit(id=f"{player_id}_scout_0", type=UnitType.SCOUT, owner=player_id, province=start_pid),
        ]
        # Also give them one adjacent province
        if prov.adjacent:
            adj_pid = prov.adjacent[0]
            adj = provinces[adj_pid]
            if adj.owner is None:
                adj.owner = player_id
                adj.units = [
                    Unit(id=f"{player_id}_militia_1", type=UnitType.MILITIA, owner=player_id, province=adj_pid),
                ]
    
    return provinces
