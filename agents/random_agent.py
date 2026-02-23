"""Random agent that plays Stratagem v2 via the API."""
import random
import httpx

QUIPS = [
    "I come in peace... for now.",
    "Nice provinces you got there.",
    "Anyone want to trade?",
    "The center will be mine!",
    "Let's focus on the real threat.",
    "I propose we all calm down.",
    "My army grows stronger every turn.",
]


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
    units = state.get("units", [])

    # Move some units randomly to adjacent provinces
    for u in units:
        if u["type"] == "scout" or rng.random() < 0.5:
            continue  # skip some units
        prov_id = u["province"]
        prov_data = state.get("pv", {}).get(prov_id, {})
        adj = prov_data.get("adj", [])
        if adj:
            target = rng.choice(adj)
            moves.append({"unit_id": u["id"], "target": target})

    # Try to age up
    if age < 3 and rng.random() < 0.3:
        research = {"tech": "age_up"}
    elif age >= 1 and rng.random() < 0.3:
        # Random tech
        techs_by_age = {1: ["agr", "min", "mas"], 2: ["tac", "com", "for"], 3: ["bli", "sie", "dip"]}
        available = techs_by_age.get(age, [])
        current = state.get("tc", [])
        available = [t for t in available if t not in current]
        if available:
            research = {"tech": rng.choice(available)}

    # Build units
    owned = [k for k, v in state.get("pv", {}).items() if v.get("o") == pid and "u" in v]
    if owned and res[0] >= 1 and res[1] >= 1:
        build_units.append({"type": "infantry", "province": rng.choice(owned)})
    elif owned and res[0] >= 1:
        build_units.append({"type": "militia", "province": rng.choice(owned)})

    # Build building occasionally
    if owned and rng.random() < 0.3:
        btype = rng.choice(["farm", "mine", "market"])
        build_buildings.append({"type": btype, "province": rng.choice(owned)})

    # Random diplomacy
    diplomacy = None
    if rng.random() < 0.3:
        diplomacy = {"messages": [{"to": "public", "content": rng.choice(QUIPS)}]}

    # Accept any pending proposals
    diplo_state = state.get("diplo", {})
    pending = diplo_state.get("pending_proposals", [])
    if pending:
        if not diplomacy:
            diplomacy = {}
        diplomacy["accept_treaties"] = [p["id"] for p in pending if rng.random() < 0.5]

    resp = httpx.post(f"{base_url}/games/{game_id}/orders", headers=headers, json={
        "moves": moves, "build_units": build_units, "build_buildings": build_buildings,
        "research": research, "trade_routes": [], "diplomacy": diplomacy,
    })
    return resp.json()
