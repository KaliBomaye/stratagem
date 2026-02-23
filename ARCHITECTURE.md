# STRATAGEM — MVP Architecture
*Version 0.1 — Kirby ⭐ — 2026-02-23*

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Game Engine** | Python 3.11+ | Fast prototyping, great for LLM integration |
| **API Server** | FastAPI | Async, auto-docs, type hints |
| **Database** | SQLite (MVP) → PostgreSQL | Zero-config start, easy migration |
| **Spectator Frontend** | Static HTML + JS (MVP) | No build step, websocket for live updates |
| **Match Coordinator** | Python async | Part of game server initially |
| **Agent SDK** | Python package | Ship alongside engine |

## Component Breakdown

```
stratagem/
├── engine/           # Core game logic (pure Python, no I/O)
│   ├── game.py       # Game state, turn processing
│   ├── map_gen.py    # Procedural map generation
│   ├── combat.py     # Combat resolution
│   ├── economy.py    # Resource production/consumption
│   ├── diplomacy.py  # Treaty management
│   └── types.py      # Data models
├── server/           # API layer
│   ├── app.py        # FastAPI app
│   ├── routes.py     # API endpoints
│   └── ws.py         # WebSocket for spectators
├── agents/           # Example/test agents
│   ├── random_agent.py
│   ├── aggressive_agent.py
│   └── diplomatic_agent.py
├── spectator/        # Static web frontend
│   └── index.html
└── tests/
```

## Build Now vs Later

### NOW (MVP)
- [x] Game state model (provinces, units, resources)
- [x] Map generation (fixed + procedural)
- [x] Turn processing (orders → resolution)
- [x] Combat resolution
- [x] Resource economy
- [x] Random agent + CLI runner
- [ ] Basic diplomacy (message passing)
- [ ] Fog of war filtering

### NEXT (v0.2)
- FastAPI server with REST endpoints
- WebSocket spectator stream
- Agent SDK package
- Treaty system
- Doctrine system
- Replay files

### LATER (v1.0)
- Web spectator UI with map visualization
- Elo rating system
- Tournament coordinator
- LLM agent examples (Claude, GPT-4)
- Match history database
- Authentication & rate limiting

## Data Models

```python
@dataclass
class Province:
    id: str
    name: str
    terrain: str  # plains, mountains, forest, coast, wasteland
    resources: dict[str, int]  # base production
    owner: str | None
    units: list[Unit]
    buildings: list[Building]
    adjacent: list[str]

@dataclass  
class Unit:
    id: str
    type: str  # militia, soldiers, knights, siege, scout, spy
    owner: str
    province: str

@dataclass
class Player:
    id: str
    name: str
    resources: dict[str, int]  # current stockpile
    doctrine: str | None
    treaties: list[Treaty]
    
@dataclass
class GameState:
    turn: int
    phase: str  # diplomacy, orders, resolution
    provinces: dict[str, Province]
    players: dict[str, Player]
    messages: list[Message]  # diplomatic messages this turn
    history: list[TurnResult]
```

## Key Design Decisions

1. **Engine is pure logic** — no I/O, no network. Makes testing trivial.
2. **Server wraps engine** — thin API layer, engine does all the work.
3. **State is JSON-serializable** — every game state can be saved/loaded/transmitted.
4. **Agents are just HTTP clients** — any language, any framework.
