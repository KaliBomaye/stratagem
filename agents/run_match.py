"""Run a full match between agents via the server API.
Supports any mix of random and LLM agents.
"""
import httpx
import random
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.random_agent import play_turn as random_play
from agents.llm_agent import play_turn as llm_play

REPLAY_DIR = Path(__file__).resolve().parent.parent / "replays"
REPLAY_DIR.mkdir(exist_ok=True)


def run_match(
    base_url: str = "http://localhost:8000",
    num_players: int = 4,
    seed: int = 42,
    max_turns: int = 40,
    llm_players: list[int] | None = None,  # indices of LLM players (e.g. [0] = p0 is LLM)
    llm_url: str = "http://localhost:18789",
    llm_model: str = "anthropic/claude-sonnet-4-6",
):
    llm_players = set(llm_players or [])

    resp = httpx.post(f"{base_url}/games", json={
        "num_players": num_players, "seed": seed, "max_turns": max_turns,
    })
    resp.raise_for_status()
    game = resp.json()
    game_id = game["game_id"]
    player_keys = game["player_keys"]
    players = list(player_keys.keys())

    print(f"🎮 Created game {game_id} with {num_players} players")
    for i, pid in enumerate(players):
        agent_type = "LLM" if i in llm_players else "Random"
        print(f"  {pid}: {agent_type}")

    rngs = {pid: random.Random(seed + i) for i, pid in enumerate(players)}

    for turn in range(max_turns + 5):
        print(f"\n--- Turn {turn + 1} ---")
        results = {}
        for i, (pid, key) in enumerate(player_keys.items()):
            if i in llm_players:
                print(f"  {pid} (LLM) thinking...")
                result = llm_play(base_url, game_id, key, llm_url, llm_model, pid)
            else:
                result = random_play(base_url, game_id, key, rngs[pid])
            results[pid] = result

            if result.get("done"):
                print(f"\n🏆 Game over! Winner: {result.get('winner')}")
                save_replay(base_url, game_id)
                return game_id

        # Check the last result for turn processing
        any_r = list(results.values())[-1]
        if any_r.get("status") == "turn_processed":
            t = any_r.get("turn", turn)
            events = any_r.get("events", [])
            print(f"  Turn {t} processed | combats={any_r.get('combats',0)} | events={len(events)}")
            for e in events:
                print(f"    {e}")
            if any_r.get("winner"):
                print(f"\n🏆 Winner: {any_r['winner']}")
                save_replay(base_url, game_id)
                return game_id
        elif any_r.get("error"):
            print(f"  Error: {any_r['error']}")
            break

    print("Game didn't finish in time")
    save_replay(base_url, game_id)
    return game_id


def save_replay(base_url: str, game_id: str):
    try:
        replay = httpx.get(f"{base_url}/games/{game_id}/replay").json()
        path = REPLAY_DIR / f"{game_id}.json"
        path.write_text(json.dumps(replay, indent=2))
        print(f"💾 Replay saved to {path}")
    except Exception as e:
        print(f"⚠️ Failed to save replay: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run a Stratagem match")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--players", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-turns", type=int, default=40)
    parser.add_argument("--llm", type=int, nargs="*", default=[], help="Player indices to use LLM (e.g. --llm 0 1)")
    parser.add_argument("--llm-url", default="http://localhost:18789")
    parser.add_argument("--llm-model", default="anthropic/claude-sonnet-4-6")
    args = parser.parse_args()

    run_match(
        base_url=args.server,
        num_players=args.players,
        seed=args.seed,
        max_turns=args.max_turns,
        llm_players=args.llm,
        llm_url=args.llm_url,
        llm_model=args.llm_model,
    )
