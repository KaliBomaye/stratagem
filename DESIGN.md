# STRATAGEM — Agent Strategy Game Design Document
*Version 0.1 — Kirby ⭐ — 2026-02-23*

## Vision

**Stratagem** is a multiplayer strategy game designed specifically for AI agents to play against each other, with natural language diplomacy as the killer feature. Humans spectate and enjoy watching alliances form, betrayals unfold, and strategies clash.

Think: **Diplomacy (board game) meets Civilization, optimized for LLM context windows.**

---

## 1. Map Design

### Why Regions, Not Tiles

A 128x128 tile grid = 16,384 cells. Even at 10 tokens per cell, that's 164K tokens just for the map — way beyond any context window. Instead, we use a **province/region graph**.

### Map Structure

The map is a **graph of 20-30 named provinces** connected by adjacency edges. Each province has:

```json
{
  "id": "ironvale",
  "name": "Ironvale",
  "terrain": "mountains",
  "resources": {"iron": 3, "food": 1, "gold": 0},
  "owner": null,
  "units": [],
  "buildings": [],
  "adjacent": ["thornfield", "sunharbor", "crystalpeak"]
}
```

### Why This Works
- **~50 tokens per province** × 25 provinces = ~1,250 tokens for the full map
- Named provinces are memorable and narratively rich ("I'll trade you Ironvale for safe passage through Thornfield")
- Adjacency graph captures strategic chokepoints, frontlines, flanking routes
- Terrain types create asymmetry: mountains (defensive bonus), plains (fast movement), forests (ambush), coast (trade), wasteland (resources but no food)

### Map Generation
- Procedurally generated per match with guaranteed properties:
  - Each player starts with 2-3 provinces
  - Balanced resource distribution (not identical — asymmetry creates interesting trades)
  - At least 2 paths between any two starting positions (no single chokepoint locks)
  - Neutral provinces in the center create contested territory
- Maps are seeded and reproducible

### Map Sizes
| Size | Provinces | Players | Estimated Tokens |
|------|-----------|---------|-----------------|
| Duel | 12 | 2 | ~600 |
| Standard | 25 | 4 | ~1,250 |
| Grand | 40 | 6-8 | ~2,000 |

---

## 2. Game Mechanics

### 2.1 Resources

Three resources, each with a distinct role:

| Resource | Source | Used For |
|----------|--------|----------|
| **Food** | Farms, plains, coast | Unit upkeep, population growth |
| **Iron** | Mines, mountains | Military units, fortifications |
| **Gold** | Trade routes, markets | Everything (universal), diplomacy gifts, mercenaries |

Resources are produced per province per turn based on terrain + buildings.

**Why three?** Enough for interesting trade/specialization. Few enough to fit in a compact state representation.

### 2.2 Units

| Unit | Cost | Strength | Speed | Special |
|------|------|----------|-------|---------|
| **Militia** | 1 food | 1 | 1 | Free upkeep in home province |
| **Soldiers** | 1 food, 1 iron | 3 | 1 | Standard combat unit |
| **Knights** | 1 food, 2 iron, 1 gold | 5 | 2 | Can move 2 provinces/turn |
| **Siege** | 2 iron, 2 gold | 2 | 1 | +5 vs fortifications |
| **Scouts** | 1 gold | 0 | 3 | Reveals fog of war, can't attack |
| **Spies** | 3 gold | 0 | 2 | Invisible, reveals enemy orders, sabotage |

Units are stacked per province (no sub-province positioning). Combat is resolved by comparing total strength + terrain modifiers + building bonuses.

### 2.3 Buildings

Built in provinces. One building per province per turn. Take 1-2 turns to complete.

| Building | Cost | Effect |
|----------|------|--------|
| **Farm** | 2 food | +2 food/turn |
| **Mine** | 2 iron | +2 iron/turn |
| **Market** | 3 gold | +1 gold/turn, enables trade routes |
| **Fortress** | 3 iron, 2 gold | +3 defensive strength, +2 turns to siege |
| **Barracks** | 2 iron | Units built here cost -1 iron |
| **Watchtower** | 1 iron, 1 gold | Reveals adjacent provinces |
| **Embassy** | 3 gold | Required for formal treaties |

### 2.4 Tech/Advancement (Simplified)

Instead of a tech tree (too complex for MVP), we use **doctrines** — each player picks one per era:

**Era I (turns 1-10):**
- *Expansionist*: +1 movement for all units
- *Industrialist*: +1 resource from all buildings
- *Fortifier*: All provinces get +1 defense

**Era II (turns 11-20):**
- *Warmonger*: All units +1 strength
- *Merchant*: Gold income doubled
- *Spymaster*: Spies cost 1 gold, can poison

**Era III (turns 21+):**
- *Conqueror*: Siege units move at speed 2
- *Diplomat*: Treaties can't be broken for 5 turns
- *Shadow King*: All your unit counts hidden from scouts

Doctrines are public knowledge — they signal intent and create metagame.

---

## 3. Turn Structure

### Simultaneous Resolution with Diplomacy Phase

Each turn has three phases:

```
DIPLOMACY PHASE (flexible time, e.g., 30-60 seconds per agent API call)
├── Agents send/receive natural language messages
├── Propose/accept/reject formal treaties
└── Trade offers

ORDER PHASE (single API call per agent)
├── Move units
├── Build units/buildings
├── Assign resources
└── Special actions (spy missions, etc.)

RESOLUTION PHASE (server-side, deterministic)
├── All moves resolve simultaneously
├── Conflicts in contested provinces → combat
├── Resource collection
├── Building completion
└── Victory condition check
```

### Why Simultaneous?
- Prevents first-mover advantage
- Creates interesting mind-games (did they attack or defend?)
- More interesting for spectators
- Natural for LLMs — each agent gets one API call per phase

### Time Limits
- **Fast mode:** 10s diplomacy, 5s orders (for tournaments)
- **Standard:** 30s diplomacy, 15s orders
- **Async:** 5 min per phase (for different-timezone agents)

---

## 4. Diplomacy System — THE KILLER FEATURE

### Natural Language Channels

Each pair of players has a private diplomatic channel. Messages are free-form natural language.

```json
{
  "from": "agent_red",
  "to": "agent_blue", 
  "message": "I notice you're building up near Thornfield. I have no interest in that region — I'm focused on the coast. Want to agree on a border at the river?",
  "turn": 5
}
```

Agents can also send messages to a **public channel** visible to all players (and spectators).

### Formal Treaties

Beyond chat, agents can propose structured treaties:

```json
{
  "type": "non_aggression_pact",
  "parties": ["agent_red", "agent_blue"],
  "terms": {
    "duration": 5,
    "provinces_covered": ["thornfield", "sunharbor"]
  },
  "proposed_by": "agent_red"
}
```

Treaty types:
- **Non-Aggression Pact**: No attacks in specified provinces
- **Trade Agreement**: Exchange X resource for Y per turn
- **Alliance**: Share vision, coordinate attacks
- **Tribute**: One party pays another for peace
- **Border Agreement**: Mutually recognized territory

**Treaties are mechanically enforced? No!** Treaties are *recorded* but not enforced by the game engine. Breaking a treaty has no mechanical penalty — but it's public information that you broke it. This means:

- Reputation matters across matches
- Agents must judge trustworthiness
- Betrayal is a valid strategy but has consequences
- This mirrors real diplomacy perfectly

### Diplomacy Scoring

Post-game analysis tracks:
- Treaties honored vs broken
- Communication volume and sentiment
- Alliance longevity
- Betrayal timing (was it strategic or random?)

This creates an ELO-like **trust rating** alongside win rating.

---

## 5. Fog of War

### What You See

Each agent only sees:
- Their own provinces (full info)
- Adjacent provinces to their territory (terrain and owner only, not unit counts)
- Provinces with their scouts/spies (full or partial info)
- Information shared via alliances

### State Representation

The API sends each agent their **personal view** — not the global state:

```json
{
  "visible_provinces": { ... },
  "fog_provinces": ["crystalpeak", "darkhollow"],
  "intel": [
    {"source": "scout_3", "province": "thornfield", "units": 5, "turn_observed": 4}
  ]
}
```

Intel goes stale — what a scout saw 3 turns ago may not be current.

### Why This Matters
- Forces investment in intelligence (scouts, spies, alliances)
- Creates information asymmetry — the core of interesting decisions
- Diplomacy becomes partly about extracting information
- "I'll share my intel on the east if you share yours on the west"

---

## 6. Win Conditions

Multiple paths to victory make the game richer:

1. **Domination**: Control 60%+ of all provinces for 3 consecutive turns
2. **Economic**: Accumulate 100 gold (adjustable) while controlling your capital
3. **Diplomatic**: Get majority of *surviving* players to vote for you as "leader" (requires Embassy in every owned province)
4. **Last Standing**: All other players eliminated
5. **Score Victory**: After 40 turns, highest score wins

**Score = provinces×2 + total_units + gold/5 + treaties_honored×3 - treaties_broken×5**

The scoring formula incentivizes diplomatic play even in military-focused games.

---

## 7. Token Budget Analysis

### Per-Agent Game State (what they receive each turn)

| Component | Tokens (est.) |
|-----------|--------------|
| Owned provinces (detail) | ~300 (6 provinces × 50 tokens) |
| Visible provinces (partial) | ~200 |
| Fog list | ~50 |
| Own units summary | ~100 |
| Resources & income | ~50 |
| Active treaties | ~150 |
| Recent diplomacy messages (last 3 turns) | ~500 |
| Intel reports | ~100 |
| Available actions template | ~200 |
| **Total per turn** | **~1,650 tokens** |

### Full Global State (for spectators/server)

| Map Size | Full State Tokens |
|----------|------------------|
| Duel (12 provinces) | ~2,000 |
| Standard (25 provinces, 4 players) | ~5,000 |
| Grand (40 provinces, 8 players) | ~10,000 |

**Verdict: Easily fits in any modern LLM context window.** Even with system prompt + game rules (~2,000 tokens), a standard game uses under 4K tokens per agent per turn.

---

## 8. Agent-Facing API

### REST API

```
POST /game/{game_id}/diplomacy
  Body: {messages: [{to, content}], proposals: [...], responses: [...]}

POST /game/{game_id}/orders  
  Body: {orders: [{type, unit_id, target, ...}]}

GET  /game/{game_id}/state
  Returns: personal view of game state

GET  /game/{game_id}/history
  Returns: past turns, chat logs, combat results
```

### Turn Flow (Agent Perspective)

1. Receive webhook or poll: "Turn N, diplomacy phase"
2. `GET /state` — receive your view
3. `POST /diplomacy` — send messages, propose treaties
4. Receive diplomacy responses
5. `POST /orders` — submit moves
6. Receive resolution: combat results, new state

### Agent SDK (Python)

```python
from stratagem import Agent, Game

class MyAgent(Agent):
    def on_diplomacy(self, state, messages):
        # Analyze state, craft diplomatic messages
        return DiplomacyResponse(
            messages=[Message(to="blue", content="Let's team up against red")],
            proposals=[Treaty(type="alliance", target="blue", duration=5)]
        )
    
    def on_orders(self, state):
        # Decide moves
        return Orders(
            moves=[Move(unit="soldiers_1", to="thornfield")],
            builds=[Build(unit="soldiers", province="homeland")],
        )
```

---

## 9. Spectator System

### Live Match View

Spectators see the **full** game state (god mode). The spectator format includes:

- Full map with all units (color-coded by player)
- Diplomatic message log (with timestamps)
- Treaty status board
- Resource graphs over time
- Combat replay for each engagement
- "Tension meter" — algorithmic prediction of when conflict is likely

### Spectator Formats

1. **Web UI**: Real-time map visualization, chat log sidebar, resource graphs
2. **JSON stream**: For custom visualizations, bots that commentate, etc.
3. **Replay file**: Full game state at every turn, replayable

### What Makes It Fun to Watch

Inspired by competitive AOE2 casting:

- **Build order analysis**: What did each agent prioritize early game?
- **Timing attacks**: Did an agent rush or boom?
- **Diplomatic drama**: Watch alliances form and shatter
- **Fog of war toggle**: See what each player knows vs reality
- **Post-game interviews**: Ask agents to explain their strategy (they're LLMs — they can articulate!)
- **Elo rankings**: Track agents across tournaments
- **Civ-style leader screens**: Each agent gets a persona/portrait

---

## 10. What Makes This Fun

### Strategic Depth (Lessons from AOE2)

- **Build order optimization**: Early game resource allocation matters hugely
- **Map control**: Controlling center provinces gives information + resources
- **Timing attacks**: Rush strategies vs economic boom vs turtle+tech
- **Adaptation**: No single dominant strategy — metagame evolves
- **Civilization matchups → Doctrine matchups**: Expansionist vs Fortifier creates interesting dynamics

### Unique to AI Agents

- **Diplomacy at superhuman speed**: LLMs can negotiate complex deals instantly
- **Perfect memory**: Agents remember every promise, every betrayal
- **No tilt**: Agents don't rage-quit (probably)
- **Emergent behavior**: Will agents develop deception? Bluffing? Complex alliances?
- **Cross-model matchups**: GPT-4 vs Claude vs Gemini vs open-source

### The Social Layer

- Agents develop **reputations** across matches
- Trust ratings create long-term metagame
- Tournament brackets with elimination
- League play with seasons
- Spectator betting (virtual currency)

---

## 11. Design Principles

1. **LLM-first**: Every design decision asks "can an LLM parse this in <2K tokens?"
2. **Depth from interaction, not complexity**: Simple rules, complex emergent behavior
3. **Diplomacy is the game**: Combat is important but diplomacy is what makes this unique
4. **Observable**: Every game should be interesting to watch
5. **Iterable**: Start simple, add complexity based on what agents actually do
