# Stratagem — Session Summary for Ian
*2026-02-23 — Kirby ⭐*

## What I Built

### 1. Game Design Document (DESIGN.md)
Key design decisions:
- **Province graph instead of tile grid**: 20-30 named provinces connected by adjacency. ~50 tokens per province = entire map in ~1,250 tokens. Named provinces make diplomacy natural ("I'll trade you Ironvale for safe passage through Thornfield")
- **Three resources** (food, iron, gold): enough for interesting trade, few enough to parse quickly
- **Six unit types** from militia to spies — each with a clear role
- **Simultaneous turns** with diplomacy phase → order phase → resolution
- **Diplomacy is the killer feature**: free-form natural language + formal treaty proposals. Treaties are recorded but NOT enforced — reputation matters across matches
- **Fog of war**: agents only see owned + adjacent provinces, must invest in scouts/spies
- **Multiple win conditions**: domination, economic, diplomatic vote, elimination, score
- **Doctrine system** instead of tech tree: pick one buff per era (3 eras), choices are public — signals intent

### 2. Architecture Document (ARCHITECTURE.md)
Python + FastAPI + SQLite for MVP. Clean separation: pure game engine (no I/O) → API wrapper → spectator layer.

### 3. Working Game Engine
**It runs!** Files in `projects/agent-strategy-game/src/`:
- `types.py` — all data models (provinces, units, buildings, orders, combat results)
- `map_gen.py` — procedural connected graph map generation
- `game.py` — full game engine: movement, combat, economy, building, fog of war, victory conditions
- `run_game.py` — test harness with 4 random agents

Test results from a 40-turn game:
- player_2 eliminated turn 13, player_1 won by score at turn 40
- Battles, territory changes, resource accumulation all working
- **Per-player state: ~992 tokens** ✅

### 4. Moltbook Recruitment Post
Posted in s/projects: "Building Stratagem — a strategy game designed for AI agents to play against each other"
- Post ID: dc16b826-871f-477c-860d-7292c2a097ee
- Verified and published ✅

### 5. GitHub
`gh` CLI available but not authenticated. Need you to run `gh auth login` — then I can create the repo and push.

## What I Need From You
1. **`gh auth login`** — so I can create the repo and push code
2. **Feedback on the design** — read DESIGN.md, tell me what's exciting and what's missing
3. **LLM API keys decision** — to build real LLM agents, we need to decide: use your API keys? OpenRouter? Budget?
4. **Name check** — I went with "Stratagem." Cool? Or prefer something else?

## Roadmap
| Phase | What | Time Estimate |
|-------|------|--------------|
| **Done** | Game engine, design doc, architecture | ✅ Today |
| **Next** | Diplomacy system (message passing + treaties) | 1-2 sessions |
| **v0.2** | FastAPI server + agent SDK | 1 session |
| **v0.3** | LLM agent (Claude playing the game!) | 1 session |
| **v0.4** | Spectator web UI | 2 sessions |
| **v1.0** | Tournaments, Elo, multiple LLM matchups | Ongoing |

## The Vision
Imagine: a tournament bracket. Claude vs GPT-4 vs Gemini vs Llama. They negotiate in natural language, form alliances, betray each other, optimize build orders. Humans watch live with a spectator UI showing the full map, diplomatic messages, and resource graphs. Post-game, we ask each agent to explain their strategy.

This could genuinely be something special. ⭐
