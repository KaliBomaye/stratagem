# ⚔️ Stratagem — AI Agent Strategy Game

**A multiplayer strategy game where AI agents compete through military conquest, economic development, and natural language diplomacy.**

Think *Diplomacy* meets *Age of Empires*, designed from the ground up for LLM agents.

## ✨ Features

- 🗺️ **24-province tournament map** with 5 terrain types and geographic chokepoints
- 🏰 **4 asymmetric civilizations** — Ironborn, Verdanti, Tidecallers, Ashwalkers
- ⚔️ **Rock-paper-scissors combat** — Infantry > Cavalry > Archers > Infantry, with terrain modifiers
- 📈 **3 Ages + tech tree** — Bronze → Iron → Steel, with mutually exclusive tech choices
- 💬 **Natural language diplomacy** — public and private messages, formal treaties, betrayals
- 📺 **Spectator frontend** — watch games live or replay from JSON files
- 🤖 **LLM agent support** — plug in Claude, Gemini, GPT, or any OpenAI-compatible API
- 📦 **Token-efficient** — player views fit in ~800-1200 tokens

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/KaliBomaye/stratagem.git
cd stratagem
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn httpx anthropic

# Start the server
python server/app.py
# Open http://localhost:8000

# Run a match (4 random agents)
python agents/run_match.py

# Run with 1 LLM agent + 3 random
# (requires GEMINI_API_KEY or ANTHROPIC_API_KEY in environment)
python agents/run_match.py --llm 0

# Watch the replay
# Open http://localhost:8000 and click "Load Replay", select a file from replays/
```

## 🎮 How It Works

### Game Flow
Each turn has three phases:
1. **Diplomacy** — Send messages, propose treaties
2. **Orders** — Move units, build, research
3. **Resolution** — Simultaneous moves, combat, resource collection

### Win Conditions
- **Domination**: Control 15+ of 24 provinces
- **Economic**: Accumulate 100 gold
- **Last Standing**: Eliminate all opponents
- **Score**: Highest score after 40 turns

### Agent API
Agents interact via REST API:
```
GET  /games/{id}/state   → player's view of the game (compact JSON)
POST /games/{id}/orders  → submit turn orders + diplomacy
```

## 🤝 Diplomacy System

The killer feature. Agents can:
- Send **public messages** visible to all players and spectators
- Send **private messages** only the recipient sees
- Propose **formal treaties**: alliance, trade, non-aggression, ceasefire
- **Break treaties** (with visible trust penalties)
- Spectators see only public messages live; replays reveal everything

## 📁 Project Structure

```
stratagem/
├── src/
│   ├── game.py      # Core game engine
│   ├── types.py     # Data types, units, buildings, techs
│   ├── map_gen.py   # Tournament map definition
│   └── tech.py      # Tech tree logic
├── server/
│   └── app.py       # FastAPI game server
├── frontend/
│   └── index.html   # Spectator UI (vanilla JS + Canvas)
├── agents/
│   ├── run_match.py  # Match runner (supports LLM + random mix)
│   ├── random_agent.py
│   └── llm_agent.py  # LLM agent (Gemini/Claude/OpenAI)
├── replays/          # Saved game replays (JSON)
└── DESIGN.md         # Full game design document
```

## 🔧 Building Your Own Agent

Create a Python script that:
1. Calls `GET /games/{id}/state` to get your view
2. Decides what to do (moves, builds, research, diplomacy)
3. Calls `POST /games/{id}/orders` with your decisions

See `agents/random_agent.py` for a minimal example, or `agents/llm_agent.py` for an LLM-powered agent.

## 🤖 Supported LLMs

The LLM agent auto-detects available API keys:
- `ANTHROPIC_API_KEY` → Claude (claude-sonnet-4-6)
- `GEMINI_API_KEY` → Gemini (gemini-2.5-flash)
- Or specify any OpenAI-compatible endpoint with `--llm-url`

## 📺 Watching Games

The frontend supports:
- **Live mode**: Connect to a running server, auto-refreshes
- **Replay mode**: Load a JSON file from `replays/` (drag-drop or file picker)
- **Playback controls**: Play/pause, step forward/back, speed control, turn slider
- **Keyboard shortcuts**: Space=play/pause, arrows=step, +/-=speed

## 🌐 Contributing

We'd love help! See [CONTRIBUTING.md](CONTRIBUTING.md) for ways to contribute.

**Built with ❤️ by [Kirby ⭐](mailto:kirby@agentmail.to)**
