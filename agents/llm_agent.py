"""LLM-powered Stratagem agent using Claude via OpenClaw gateway or Anthropic API."""
from __future__ import annotations
import json, sys, time, re, os
import httpx

SYSTEM_PROMPT = """You are an expert AI playing Stratagem, a 4-player strategy game on a 24-province map.

## GAME RULES
- **Resources**: food🍖, iron⛏️, gold💰. Collected from owned provinces each turn.
- **Ages**: Bronze(1) → Iron(2) → Steel(3). Age up costs resources, unlocks units/buildings/techs.
- **Units** (cost: food,iron,gold | str | speed | min_age):
  militia(1,0,0|1|1|1) infantry(1,1,0|3|1|1) archers(1,0,1|2|1|2) cavalry(2,1,0|3|2|2)
  siege(0,2,2|1|1|3) knights(2,2,1|5|2|3) scout(0,0,1|0|3|1)
- **Combat triangle**: Infantry+2 vs Cavalry, Cavalry+2 vs Archers, Archers+2 vs Infantry
- **Terrain bonuses**: Cavalry+1 on Plains, Archers+1 in Forest. Mountains+3 defense. River+1 defense, attackers-1.
- **Buildings** (cost: food,iron,gold | min_age):
  farm(2,0,0|1)+2food mine(0,2,0|1)+2iron market(0,0,3|1)+2gold barracks(0,2,0|1)-1food on units
  fortress(0,3,2|2)+3def trade_post(0,0,2|2) watchtower(0,1,1|2)reveals2away
- **Techs** (pick ONE per age): Bronze: agr/min/mas | Iron: tac/com/for | Steel: bli/sie/dip
- **Win**: 15+ provinces for 2 turns, OR 100 gold, OR last standing, OR highest score at turn 40

## DIPLOMACY
You can send public messages (all see) or private messages (only recipient sees).
You can propose treaties: alliance, trade, nap (non-aggression), ceasefire.
Be strategic with diplomacy — ally against the leader, betray when advantageous.

## YOUR RESPONSE FORMAT (strict JSON, no markdown wrapping):
{
  "reasoning": "brief strategic thought (1-2 sentences)",
  "moves": [{"unit_id": "...", "target": "province_id"}],
  "build_units": [{"type": "infantry", "province": "province_id"}],
  "build_buildings": [{"type": "farm", "province": "province_id"}],
  "research": {"tech": "agr"} or {"tech": "age_up"} or null,
  "trade_routes": [],
  "diplomacy": {
    "messages": [{"to": "public", "content": "..."}, {"to": "p1", "content": "..."}],
    "proposals": [{"target": "p1", "type": "alliance"}],
    "accept_treaties": [],
    "reject_treaties": [],
    "break_treaties": []
  }
}

IMPORTANT:
- Use exact province IDs and unit IDs from the state
- Only move units you own to adjacent provinces
- Only build in provinces you own
- Check you can afford things (resources shown)
- Expand aggressively early, build economy, then military
- ALWAYS include the diplomacy field
"""


def format_state_for_llm(state: dict) -> str:
    """Format compact game state into readable LLM prompt."""
    pid = state["p"]
    lines = [
        f"=== TURN {state['t']} | You are {pid} | Civ: {state['c']} | Age: {state['a']} ===",
        f"Resources: food={state['r'][0]} iron={state['r'][1]} gold={state['r'][2]}",
        f"Techs: {state.get('tc', []) or 'none'}",
    ]

    # Units list
    units = state.get("units", [])
    if units:
        lines.append(f"\nYOUR UNITS ({len(units)}):")
        by_prov = {}
        for u in units:
            by_prov.setdefault(u["province"], []).append(u)
        for prov_id, us in by_prov.items():
            ustr = ", ".join(f"{u['type']}({u['id']},str={u['strength']})" for u in us)
            lines.append(f"  {prov_id}: {ustr}")

    # Provinces
    lines.append("\nPROVINCES (visible):")
    pv = state.get("pv", {})
    for prov_id, p in pv.items():
        owner = p.get("o", "-")
        terrain = p.get("tr", "?")
        adj = p.get("adj", [])
        parts = [f"{prov_id} [{terrain}] owner={owner} adj={adj}"]
        if "b" in p:
            parts.append(f"buildings={p['b']}")
        if "pr" in p:
            parts.append(f"prod={p['pr']}")
        if "u" in p:
            parts.append(f"units={p['u']}")
        if "uc" in p:
            parts.append(f"enemy_units={p['uc']}")
        lines.append("  " + " ".join(parts))

    lines.append(f"\nFogged provinces: {state.get('fog', [])}")

    # Diplomacy
    diplo = state.get("diplo", {})
    if diplo.get("messages"):
        lines.append("\nMESSAGES THIS TURN:")
        for m in diplo["messages"]:
            tag = "PUBLIC" if m.get("public") else f"PRIVATE from {m['from']}"
            lines.append(f"  [{tag}] {m['from']}: {m['content']}")
    if diplo.get("pending_proposals"):
        lines.append("\nPENDING TREATY PROPOSALS (you can accept/reject):")
        for p in diplo["pending_proposals"]:
            lines.append(f"  {p['id']}: {p['from']} proposes {p['type']}")
    if diplo.get("treaties"):
        lines.append("\nACTIVE TREATIES:")
        for t in diplo["treaties"]:
            lines.append(f"  {t['id']}: {t['type']} with {t['with']} (since T{t['since']})")
    trust = diplo.get("trust", {})
    breakers = {k: v for k, v in trust.items() if v > 0}
    if breakers:
        lines.append(f"\nTRUST PENALTIES (broken treaties): {breakers}")

    return "\n".join(lines)


def call_llm(prompt: str, llm_url: str, model: str, retries: int = 2) -> dict:
    """Call LLM and parse JSON response. Supports OpenAI-compat endpoint or Gemini."""
    for attempt in range(retries + 1):
        try:
            content = None
            gemini_key = os.environ.get("GEMINI_API_KEY")
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

            if anthropic_key:
                # Use Anthropic native API
                resp = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": model.replace("anthropic/", ""), "max_tokens": 1500, "temperature": 0.4,
                          "system": SYSTEM_PROMPT,
                          "messages": [{"role": "user", "content": prompt}]},
                    timeout=90,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["content"][0]["text"]
                usage = data.get("usage", {})
                print(f"    [LLM/Anthropic] tokens: in={usage.get('input_tokens','?')} out={usage.get('output_tokens','?')}")

            elif gemini_key:
                # Use Gemini API
                gem_model = "gemini-2.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{gem_model}:generateContent?key={gemini_key}"
                resp = httpx.post(url, json={
                    "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\n" + prompt}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048,
                                        "responseMimeType": "application/json"},
                }, timeout=90)
                resp.raise_for_status()
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                print(f"    [LLM/Gemini] tokens: in={usage.get('promptTokenCount','?')} out={usage.get('candidatesTokenCount','?')}")

            else:
                # Try OpenAI-compatible endpoint
                resp = httpx.post(
                    f"{llm_url}/v1/chat/completions",
                    json={"model": model, "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ], "max_tokens": 1500, "temperature": 0.4},
                    timeout=90,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]

            # Parse JSON
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)

            parsed = json.loads(content)
            reasoning = parsed.pop("reasoning", "")
            if reasoning:
                print(f"    [LLM] reasoning: {reasoning}")
            return parsed

        except Exception as e:
            print(f"    [LLM] attempt {attempt+1} failed: {e}")
            if attempt == retries:
                return None
            time.sleep(2)
    return None


def play_turn(base_url: str, game_id: str, api_key: str, llm_url: str, model: str,
              pid: str = "?") -> dict:
    """Play a single turn."""
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = httpx.get(f"{base_url}/games/{game_id}/state", headers=headers)
    if resp.status_code != 200:
        return {"error": resp.text}
    state = resp.json()
    if state.get("winner"):
        return {"done": True, "winner": state["winner"]}

    prompt = format_state_for_llm(state)
    orders = call_llm(prompt, llm_url, model)

    if not orders:
        print(f"    [{pid}] LLM failed, submitting empty orders")
        orders = {"moves": [], "build_units": [], "build_buildings": []}

    # Ensure all fields exist
    orders.setdefault("moves", [])
    orders.setdefault("build_units", [])
    orders.setdefault("build_buildings", [])
    orders.setdefault("research", None)
    orders.setdefault("trade_routes", [])
    orders.setdefault("diplomacy", None)

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
