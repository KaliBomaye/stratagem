"""LLM-powered Stratagem agent using Claude Sonnet."""
from __future__ import annotations
import json, sys, time, re
import httpx

SYSTEM_PROMPT = """You are an AI playing Stratagem, a competitive strategy game. You control provinces, units, and resources.

RULES:
- Each turn you submit orders: move units, build units, build buildings
- Unit types: militia (str 1, cost 1 food), soldiers (str 3, cost 1 food + 1 iron), knights (str 5, cost 1 food + 2 iron + 1 gold), siege (str 2, cost 2 iron + 2 gold), scout (str 0, cost 1 gold)
- Building types: farm (+2 food), mine (+2 iron), market (+1 gold), fortress (+3 defense), barracks (-1 iron on units), watchtower (reveals adjacent), embassy (diplomacy)
- Combat: total strength + terrain bonus (mountains +2, forest +1). Defender gets terrain bonus.
- Win conditions: domination (60% provinces for 3 turns), last standing, or highest score at turn 40
- Score = provinces×2 + units + gold/5

STRATEGY TIPS:
- Control more provinces = more resources = more units
- Build soldiers early for expansion
- Defend key provinces with fortresses
- Balance expansion with economy

You MUST respond with ONLY a valid JSON object (no markdown, no explanation):
{
  "moves": [{"unit_id": "...", "target_province": "..."}],
  "build_units": [{"unit_type": "soldiers", "province": "..."}],
  "build_buildings": [{"building_type": "farm", "province": "..."}],
  "diplomacy": [{"to": "player_X", "content": "..."}]
}
"""

def format_state(state: dict) -> str:
    """Format game state as a concise prompt."""
    lines = [f"Turn {state['turn']} | You are {state['player']}"]
    lines.append(f"Resources: food={state['resources'].get('food',0)}, iron={state['resources'].get('iron',0)}, gold={state['resources'].get('gold',0)}")
    
    lines.append("\nYOUR PROVINCES:")
    for pid, prov in state["provinces"].items():
        if prov.get("owner") == state["player"] and "units" in prov:
            units_str = ", ".join(f"{u['type']}({u['id']})" for u in prov.get("units", []))
            prod = prov.get("production", {})
            lines.append(f"  {prov['name']} ({pid}) [{prov['terrain']}] units=[{units_str}] prod={prod} adj={prov.get('adjacent',[])}") 
    
    lines.append("\nVISIBLE ENEMY/NEUTRAL:")
    for pid, prov in state["provinces"].items():
        if prov.get("owner") != state["player"]:
            owner = prov.get("owner", "neutral")
            lines.append(f"  {prov['name']} ({pid}) [{prov['terrain']}] owner={owner} adj={prov.get('adjacent',[])}") 
    
    lines.append(f"\nFog: {len(state.get('fog', []))} hidden provinces")
    
    if state.get("pending_diplomacy"):
        lines.append("\nDIPLOMATIC MESSAGES:")
        for m in state["pending_diplomacy"]:
            lines.append(f"  From {m['from']}: {m['content']}")
    
    return "\n".join(lines)


def get_llm_orders(state: dict, llm_url: str = "http://localhost:18789", model: str = "anthropic/claude-sonnet-4-6") -> dict:
    """Call LLM to get orders."""
    prompt = format_state(state)
    
    resp = httpx.post(
        f"{llm_url}/v1/chat/completions",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.3,
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    
    # Parse JSON from response (handle markdown wrapping)
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    
    return json.loads(content)


def play_turn(base_url: str, game_id: str, api_key: str, llm_url: str, model: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"}
    
    resp = httpx.get(f"{base_url}/games/{game_id}/state", headers=headers)
    if resp.status_code != 200:
        return {"error": resp.text}
    state = resp.json()
    
    if state.get("winner"):
        return {"done": True, "winner": state["winner"]}
    
    try:
        orders = get_llm_orders(state, llm_url, model)
    except Exception as e:
        print(f"  LLM error: {e}, submitting empty orders")
        orders = {"moves": [], "build_units": [], "build_buildings": []}
    
    # Submit diplomacy first
    diplo = orders.pop("diplomacy", [])
    if diplo:
        httpx.post(f"{base_url}/games/{game_id}/diplomacy", headers=headers, json={"messages": diplo})
    
    # Submit orders
    resp = httpx.post(f"{base_url}/games/{game_id}/orders", headers=headers, json=orders)
    return resp.json()


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    game_id = sys.argv[2] if len(sys.argv) > 2 else None
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    llm_url = sys.argv[4] if len(sys.argv) > 4 else "http://localhost:18789"
    model = sys.argv[5] if len(sys.argv) > 5 else "anthropic/claude-sonnet-4-6"
    
    if not game_id or not api_key:
        print("Usage: llm_agent.py <base_url> <game_id> <api_key> [llm_url] [model]")
        sys.exit(1)
    
    print(f"LLM Agent starting: game={game_id}, model={model}")
    while True:
        result = play_turn(base_url, game_id, api_key, llm_url, model)
        print(f"  Result: {result}")
        if result.get("done") or result.get("error"):
            break
        if result.get("status") == "waiting":
            time.sleep(1)
            continue
        time.sleep(0.5)


if __name__ == "__main__":
    main()
