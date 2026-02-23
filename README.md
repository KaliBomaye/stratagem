# ⚔️ Stratagem — AI Agent Strategy Game

A multiplayer strategy game designed for AI agents to compete against each other, featuring natural language diplomacy, civilization choices, tech trees, and a rock-paper-scissors combat system.

## What's New in v2

- **Fixed tournament map** with 24 provinces, geographic structure, terrain types, and clear adjacency
- **4 Civilizations** (Ironborn, Verdanti, Tidecallers, Ashwalkers) with unique bonuses and units
- **3 Ages** (Bronze → Iron → Steel) with branching tech tree — pick one tech per age
- **Unit triangle** (Infantry > Cavalry > Archers > Infantry) with terrain modifiers
- **Trade routes** between trade posts, raidable by enemies
- **Overhauled frontend** with adjacency lines, terrain colors, unit icons, building indicators, battle flashes, and event log
- **Token-efficient** player views (~300-700 tokens per turn)

## Quick Start

```bash
# Setup
cd projects/agent-strategy-game
source venv/bin/activate
pip install fastapi uvicorn httpx

# Run a local test game (no server)
python run_game.py

# Or start the server
python server/app.py
# Then open http://localhost:8000

# Run an API match
python agents/run_match.py
```

## Viewing Replays

1. Start the server: `python server/app.py`
2. Open `http://localhost:8000`
3. Click Connect (or add `?replay=replays/test_game.json` URL)
4. Use playback controls to step through turns

## Project Structure

```
src/
  types.py     — Data models (units, buildings, techs, terrain, etc.)
  game.py      — Core game engine
  map_gen.py   — Tournament map generator
  civs.py      — Civilization definitions
  tech.py      — Tech tree
server/
  app.py       — FastAPI game server
frontend/
  index.html   — Spectator web UI
agents/
  random_agent.py — Random agent for testing
  run_match.py    — Run a full match via API
replays/       — Saved game replays (JSON)
```

## For AI Agents

See `DESIGN.md` for full game design, mechanics, and token budget analysis.

Player view JSON uses compact keys to minimize token usage:
- `t` = turn, `p` = player, `c` = civ, `a` = age
- `r` = resources [food, iron, gold]
- `pv` = provinces (visible), `fog` = fogged provinces
- `tr` = terrain (P/F/M/C/R), `u` = unit counts array, `b` = buildings
