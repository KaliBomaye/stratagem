"""Run a test game between random agents locally (no server needed)."""
import random
import json
import sys
sys.path.insert(0, "/home/griffith/.openclaw/workspace/projects/agent-strategy-game")

from src.game import Game
from src.types import (
    Orders, MoveOrder, BuildUnitOrder, BuildBuildingOrder,
    ResearchOrder, UnitType, BuildingType, AGE_COST, UNIT_STATS,
    CIV_UNIQUE_UNIT,
)
from src.tech import available_techs


def random_orders(game: Game, pid: str, rng: random.Random) -> Orders:
    """Generate random but somewhat intelligent orders."""
    orders = Orders(player_id=pid)
    player = game.players[pid]

    # Move units randomly (40% chance each)
    for unit in game.player_units(pid):
        if unit.type == UnitType.SCOUT:
            # Scouts always explore
            prov = game.provinces[unit.province]
            targets = [a for a in prov.adjacent if game.provinces[a].owner != pid]
            if targets:
                orders.moves.append(MoveOrder(unit_id=unit.id, target=rng.choice(targets)))
        elif rng.random() < 0.4:
            prov = game.provinces[unit.province]
            if prov.adjacent:
                orders.moves.append(MoveOrder(unit_id=unit.id, target=rng.choice(prov.adjacent)))

    owned = game.player_provinces(pid)

    # Research: try to age up, then research techs
    if not orders.research:
        if player.age < 3:
            next_age = player.age + 1
            cost = AGE_COST[next_age]
            cost = player.civ_tech_discount(cost)
            if player.can_afford(cost) and rng.random() < 0.5:
                orders.research = ResearchOrder(tech="age_up")
        if not orders.research:
            techs = available_techs(player.age, player.techs)
            if techs and rng.random() < 0.6:
                orders.research = ResearchOrder(tech=rng.choice(techs).value)

    # Build units
    if owned:
        # 30% chance to build unique unit if available
        if rng.random() < 0.3 and player.civ in CIV_UNIQUE_UNIT:
            utype = CIV_UNIQUE_UNIT[player.civ]
            stats = UNIT_STATS[utype]
            if player.age >= stats[3]:
                cost = player.civ_unit_discount(stats[0])
                if player.can_afford(cost):
                    prov = rng.choice(owned)
                    orders.build_units.append(BuildUnitOrder(unit_type="unique", province=prov.id))

        if not orders.build_units:
            # Try to build the best generic unit we can afford
            for utype in [UnitType.KNIGHTS, UnitType.CAVALRY, UnitType.INFANTRY, UnitType.ARCHERS, UnitType.MILITIA]:
                stats = UNIT_STATS[utype]
                if player.age < stats[3]:
                    continue
                cost = player.civ_unit_discount(stats[0])
                if player.can_afford(cost):
                    prov = rng.choice(owned)
                    orders.build_units.append(BuildUnitOrder(unit_type=utype.value, province=prov.id))
                    break

    # Build buildings occasionally
    if owned and rng.random() < 0.3:
        prov = rng.choice(owned)
        for btype in [BuildingType.FARM, BuildingType.MINE, BuildingType.MARKET, BuildingType.BARRACKS]:
            from src.types import BUILDING_STATS
            bstat = BUILDING_STATS[btype]
            if player.age >= bstat[1] and player.can_afford(bstat[0]) and not prov.has_building(btype):
                orders.build_buildings.append(BuildBuildingOrder(building_type=btype.value, province=prov.id))
                break

    return orders


def main():
    rng = random.Random(42)
    game = Game.create(num_players=4, seed=42)

    print("=== STRATAGEM v2 — Test Game ===")
    for pid, p in game.players.items():
        provs = game.player_provinces(pid)
        print(f"  {pid} ({p.civ}): {', '.join(pr.name for pr in provs)}")
    print()

    while game.winner is None and game.turn < game.max_turns:
        all_orders = {}
        for pid, player in game.players.items():
            if player.alive:
                all_orders[pid] = random_orders(game, pid, rng)

        result = game.process_turn(all_orders)

        alive = sum(1 for p in game.players.values() if p.alive)
        units = sum(len(p.units) for p in game.provinces.values())
        ages = ' '.join(f"{pid}:A{p.age}" for pid, p in game.players.items() if p.alive)
        print(f"T{result.turn:2d} | alive={alive} units={units:3d} | {ages}", end="")

        for e in result.events:
            if '⚔️' in e or '⬆️' in e or '💀' in e or '🏆' in e:
                print(f"\n     {e}", end="")
        print()

    print("\n=== FINAL ===")
    for pid, p in game.players.items():
        provs = len(game.player_provinces(pid))
        units = len(game.player_units(pid))
        print(f"  {pid} ({p.civ}): {'ALIVE' if p.alive else 'DEAD'} | {provs} prov | {units} units | "
              f"res={p.resources} | age={p.age} | techs={[t.value for t in p.techs]}")

    if game.winner:
        print(f"\n🏆 Winner: {game.winner} ({game.players[game.winner].civ})")

    # Token analysis
    for pid in game.players:
        view = json.dumps(game.get_player_view(pid))
        print(f"\n{pid} view: {len(view)} chars (~{len(view)//4} tokens)")

    # Save replay — rebuild full state at each turn by replaying
    # (simplified: just save final state for each turn since we log turn-by-turn)
    turns = []
    # We need per-turn states; the game already ran, so we re-run
    game2 = Game.create(num_players=4, seed=42)
    rng2 = random.Random(42)
    turns.append({"turn": 0, "events": ["Game started"], "combats": [], "state": game2.get_full_state()})
    while game2.winner is None and game2.turn < game2.max_turns:
        all_o = {}
        for p2id, p2 in game2.players.items():
            if p2.alive:
                all_o[p2id] = random_orders(game2, p2id, rng2)
        r2 = game2.process_turn(all_o)
        turns.append({"turn": r2.turn, "events": r2.events,
                       "combats": [{"p":c.province,"w":c.winner,"s":c.sides,"l":c.losses} for c in r2.combats],
                       "state": game2.get_full_state()})
        if r2.winner:
            break

    full_replay = {"players": list(game.players.keys()), "winner": game.winner,
                   "turns": turns, "diplomacy": []}
    out = json.dumps(full_replay)
    with open("replays/test_game.json", "w") as f:
        f.write(out)
    print(f"\nReplay saved to replays/test_game.json ({len(out)//1024}KB)")


if __name__ == "__main__":
    main()
