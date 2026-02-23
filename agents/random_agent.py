"""Random agent that plays Stratagem via the API."""
import random
import httpx
import time
import sys

def play_turn(base_url: str, game_id: str, api_key: str, rng: random.Random) -> dict:
    """Get state, generate random orders, submit."""
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Get state
    resp = httpx.get(f"{base_url}/games/{game_id}/state", headers=headers)
    if resp.status_code != 200:
        return {"error": resp.text}
    state = resp.json()
    
    if state.get("winner"):
        return {"done": True, "winner": state["winner"]}
    
    moves = []
    build_units = []
    
    # Move units randomly
    for pid, prov in state["provinces"].items():
        if "units" not in prov:
            continue
        for unit in prov.get("units", []):
            if unit["owner"] != state["player"] or unit["type"] == "scout":
                continue
            if rng.random() < 0.4:
                adj = prov.get("adjacent", [])
                if adj:
                    moves.append({"unit_id": unit["id"], "target_province": rng.choice(adj)})
    
    # Build soldiers if affordable
    resources = state.get("resources", {})
    owned = [pid for pid, p in state["provinces"].items() if p.get("owner") == state["player"] and "units" in p]
    if owned and resources.get("food", 0) >= 1 and resources.get("iron", 0) >= 1:
        build_units.append({"unit_type": "soldiers", "province": rng.choice(owned)})
    
    # Submit orders
    resp = httpx.post(f"{base_url}/games/{game_id}/orders", headers=headers, json={
        "moves": moves, "build_units": build_units, "build_buildings": []
    })
    return resp.json()


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    game_id = sys.argv[2] if len(sys.argv) > 2 else None
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not game_id or not api_key:
        print("Usage: random_agent.py <base_url> <game_id> <api_key>")
        sys.exit(1)
    
    rng = random.Random()
    while True:
        result = play_turn(base_url, game_id, api_key, rng)
        print(f"Turn result: {result}")
        if result.get("done") or result.get("error"):
            break
        if result.get("status") == "waiting":
            time.sleep(0.5)
            continue
        time.sleep(0.1)


if __name__ == "__main__":
    main()
