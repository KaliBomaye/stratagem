"""Run a full match between agents via the server API."""
import httpx
import random
import time
import json
import sys
import threading

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from agents.random_agent import play_turn as random_play_turn

def run_random_match(base_url: str = "http://localhost:8000", num_players: int = 4, seed: int = 42):
    """Create a game and run random agents to completion."""
    # Create game
    resp = httpx.post(f"{base_url}/games", json={"num_players": num_players, "num_provinces": 20, "seed": seed, "max_turns": 40})
    resp.raise_for_status()
    game = resp.json()
    game_id = game["game_id"]
    player_keys = game["player_keys"]
    print(f"Created game {game_id} with {num_players} players")
    
    rngs = {pid: random.Random(seed + i) for i, pid in enumerate(player_keys)}
    
    turn = 0
    while turn < 45:  # safety limit
        results = {}
        for pid, key in player_keys.items():
            result = random_play_turn(base_url, game_id, key, rngs[pid])
            results[pid] = result
            if result.get("done"):
                print(f"\n🏆 Game over! Winner: {result.get('winner')}")
                # Get replay
                replay = httpx.get(f"{base_url}/games/{game_id}/replay").json()
                out_path = f"replays/{game_id}.json"
                with open(out_path, "w") as f:
                    json.dump(replay, f, indent=2)
                print(f"Replay saved to {out_path}")
                return game_id
        
        # Check if turn was processed
        any_result = list(results.values())[0]
        if any_result.get("status") == "turn_processed":
            turn = any_result.get("turn", turn + 1)
            print(f"Turn {turn} | combats={any_result.get('combats', 0)} | elim={any_result.get('eliminations', [])}" + 
                  (f" | WINNER: {any_result['winner']}" if any_result.get('winner') else ""))
            if any_result.get("winner"):
                replay = httpx.get(f"{base_url}/games/{game_id}/replay").json()
                out_path = f"replays/{game_id}.json"
                with open(out_path, "w") as f:
                    json.dump(replay, f, indent=2)
                print(f"Replay saved to {out_path}")
                return game_id
    
    print("Game didn't finish in time")
    return game_id


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    run_random_match(base_url)
