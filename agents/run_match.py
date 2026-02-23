"""Run a full match between agents via the server API."""
import httpx
import random
import json
import sys

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from agents.random_agent import play_turn

def run_random_match(base_url: str = "http://localhost:8000", num_players: int = 4, seed: int = 42):
    resp = httpx.post(f"{base_url}/games", json={
        "num_players": num_players, "seed": seed, "max_turns": 40,
    })
    resp.raise_for_status()
    game = resp.json()
    game_id = game["game_id"]
    player_keys = game["player_keys"]
    print(f"Created game {game_id} with {num_players} players")

    rngs = {pid: random.Random(seed + i) for i, pid in enumerate(player_keys)}

    for turn in range(50):
        results = {}
        for pid, key in player_keys.items():
            result = play_turn(base_url, game_id, key, rngs[pid])
            results[pid] = result
            if result.get("done"):
                print(f"\n🏆 Game over! Winner: {result.get('winner')}")
                save_replay(base_url, game_id)
                return game_id

        any_r = list(results.values())[0]
        if any_r.get("status") == "turn_processed":
            t = any_r.get("turn", turn)
            print(f"Turn {t} | combats={any_r.get('combats',0)} | events={len(any_r.get('events',[]))}")
            if any_r.get("winner"):
                print(f"🏆 Winner: {any_r['winner']}")
                save_replay(base_url, game_id)
                return game_id

    print("Game didn't finish")
    return game_id

def save_replay(base_url, game_id):
    replay = httpx.get(f"{base_url}/games/{game_id}/replay").json()
    with open(f"replays/{game_id}.json", "w") as f:
        json.dump(replay, f)
    print(f"Replay saved to replays/{game_id}.json")

if __name__ == "__main__":
    run_random_match(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
