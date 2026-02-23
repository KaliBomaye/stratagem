"""Run a test game between random agents."""
import random
import json
import sys
sys.path.insert(0, "/home/griffith/.openclaw/workspace/projects/agent-strategy-game")

from src.game import Game
from src.types import Orders, MoveOrder, BuildUnitOrder, UnitType


def random_orders(game: Game, player_id: str, rng: random.Random) -> Orders:
    """Generate random but valid orders for a player."""
    orders = Orders(player_id=player_id)
    player = game.players[player_id]
    
    # Move some units randomly
    units = game.get_player_units(player_id)
    for unit in units:
        if rng.random() < 0.4:  # 40% chance to move each unit
            prov = game.provinces[unit.province]
            if prov.adjacent:
                target = rng.choice(prov.adjacent)
                orders.moves.append(MoveOrder(unit_id=unit.id, target_province=target))
    
    # Build units in owned provinces
    owned = game.get_player_provinces(player_id)
    if owned and player.resources.get("food", 0) >= 1 and player.resources.get("iron", 0) >= 1:
        prov = rng.choice(owned)
        orders.build_units.append(BuildUnitOrder(unit_type=UnitType.SOLDIERS, province=prov.id))
    
    return orders


def main():
    rng = random.Random(42)
    game = Game.create(num_players=4, num_provinces=20, seed=42)
    
    print("=== STRATAGEM — Test Game ===")
    print(f"Players: {list(game.players.keys())}")
    print(f"Provinces: {len(game.provinces)}")
    print()
    
    # Show starting positions
    for pid in game.players:
        provs = game.get_player_provinces(pid)
        units = game.get_player_units(pid)
        print(f"  {pid}: {len(provs)} provinces ({', '.join(p.name for p in provs)}), {len(units)} units")
    print()
    
    # Run game
    while game.winner is None and game.turn < game.max_turns:
        all_orders = {}
        for pid, player in game.players.items():
            if player.alive:
                all_orders[pid] = random_orders(game, pid, rng)
        
        result = game.process_turn(all_orders)
        
        # Print turn summary
        alive = sum(1 for p in game.players.values() if p.alive)
        total_units = sum(len(p.units) for p in game.provinces.values())
        print(f"Turn {result.turn:2d} | Alive: {alive} | Units: {total_units:3d} | Combats: {len(result.combats)}", end="")
        
        for combat in result.combats:
            print(f" | Battle at {game.provinces[combat.province].name}: {combat.winner} wins", end="")
        
        if result.eliminations:
            print(f" | ELIMINATED: {', '.join(result.eliminations)}", end="")
        
        if result.winner:
            print(f" | *** WINNER: {result.winner} ***", end="")
        
        print()
    
    # Final state
    print()
    print("=== FINAL STATE ===")
    for pid, player in game.players.items():
        provs = game.get_player_provinces(pid)
        units = game.get_player_units(pid)
        print(f"  {pid}: {'ALIVE' if player.alive else 'DEAD'} | {len(provs)} provinces | {len(units)} units | Resources: {player.resources}")
    
    if game.winner:
        print(f"\n🏆 Winner: {game.winner}")
    else:
        print("\n⏰ Game ended by turn limit")
    
    # Show sample player view (token count)
    print()
    state_json = json.dumps(game.get_state_for_player("player_0"), indent=2)
    # Rough token estimate: ~4 chars per token for JSON
    print(f"Player view JSON: {len(state_json)} chars (~{len(state_json)//4} tokens)")


if __name__ == "__main__":
    main()
