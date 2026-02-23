"""Random agent that plays Stratagem v2 via the API."""
import random
import httpx
import sys

def play_turn(base_url: str, game_id: str, api_key: str, rng: random.Random) -> dict:
    """Get state, generate random orders, submit."""
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = httpx.get(f"{base_url}/games/{game_id}/state", headers=headers)
    if resp.status_code != 200:
        return {"error": resp.text}
    state = resp.json()
    if state.get("winner"):
        return {"done": True, "winner": state["winner"]}

    moves = []
    build_units = []
    build_buildings = []
    research = None

    pid = state["p"]
    res = state["r"]  # [food, iron, gold]
    age = state["a"]

    # Move units
    for prov_id, prov in state.get("pv", {}).items():
        if "u" not in prov or prov.get("o") != pid:
            continue
        # We have unit counts but not individual IDs in compact view
        # For API play, we need the full state endpoint — skip moves for random agent
        # (In real agent play, you'd use the full unit list)

    # Try to age up
    if age < 3 and rng.random() < 0.4:
        research = {"tech": "age_up"}

    # Build infantry if affordable
    owned = [k for k, v in state.get("pv", {}).items() if v.get("o") == pid and "u" in v]
    if owned and res[0] >= 1 and res[1] >= 1:
        build_units.append({"type": "infantry", "province": rng.choice(owned)})

    # Build farm occasionally
    if owned and res[0] >= 2 and rng.random() < 0.3:
        build_buildings.append({"type": "farm", "province": rng.choice(owned)})

    resp = httpx.post(f"{base_url}/games/{game_id}/orders", headers=headers, json={
        "moves": moves, "build_units": build_units, "build_buildings": build_buildings,
        "research": research, "trade_routes": [],
    })
    return resp.json()
