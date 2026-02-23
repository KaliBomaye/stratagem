"""Stratagem Game Server v2 — FastAPI."""
from __future__ import annotations
import json, time, uuid, secrets
from pathlib import Path
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.game import Game
from src.types import (
    Orders, MoveOrder, BuildUnitOrder, BuildBuildingOrder,
    ResearchOrder, TradeRouteOrder,
)

app = FastAPI(title="Stratagem", version="2.0.0")

# ── Data stores ──────────────────────────────────────────────────────────────

@dataclass
class GameInstance:
    id: str
    game: Game
    player_keys: dict[str, str]
    spectator_key: str
    pending_orders: dict[str, Orders] = field(default_factory=dict)
    diplo_log: list[dict] = field(default_factory=list)
    turn_log: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

GAMES: dict[str, GameInstance] = {}
REPLAY_DIR = Path(__file__).resolve().parent.parent / "replays"
REPLAY_DIR.mkdir(exist_ok=True)

# ── Auth ─────────────────────────────────────────────────────────────────────

def get_player(game_id: str, authorization: str) -> tuple[GameInstance, str]:
    token = authorization.replace("Bearer ", "")
    gi = GAMES.get(game_id)
    if not gi:
        raise HTTPException(404, "Game not found")
    for pid, key in gi.player_keys.items():
        if key == token:
            return gi, pid
    raise HTTPException(403, "Invalid API key")

# ── Models ───────────────────────────────────────────────────────────────────

class CreateGameRequest(BaseModel):
    num_players: int = 4
    seed: int | None = None
    max_turns: int = 40
    civs: list[str] | None = None

class SubmitOrdersRequest(BaseModel):
    moves: list[dict] = []
    build_units: list[dict] = []
    build_buildings: list[dict] = []
    research: dict | None = None
    trade_routes: list[dict] = []

class DiplomacyMessage(BaseModel):
    to: str
    content: str

class SubmitDiplomacyRequest(BaseModel):
    messages: list[DiplomacyMessage] = []

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/games")
def create_game(req: CreateGameRequest):
    gid = str(uuid.uuid4())[:8]
    game = Game.create(num_players=req.num_players, seed=req.seed, civs=req.civs)
    game.max_turns = req.max_turns

    player_keys = {pid: secrets.token_hex(16) for pid in game.players}
    spectator_key = secrets.token_hex(16)
    gi = GameInstance(id=gid, game=game, player_keys=player_keys, spectator_key=spectator_key)
    gi.turn_log.append({"turn": 0, "events": ["Game created"], "state": game.get_full_state()})
    GAMES[gid] = gi

    return {
        "game_id": gid,
        "player_keys": player_keys,
        "spectator_key": spectator_key,
        "players": list(game.players.keys()),
    }

@app.get("/games/{game_id}/state")
def get_state(game_id: str, authorization: str = Header(...)):
    gi, pid = get_player(game_id, authorization)
    state = gi.game.get_player_view(pid)
    state["diplo"] = [m for m in gi.diplo_log
                      if m["turn"] == gi.game.turn and (m["to"] == pid or m["to"] == "public")]
    state["game_id"] = game_id
    state["winner"] = gi.game.winner
    return state

@app.get("/games/{game_id}/spectator")
def get_spectator_state(game_id: str):
    gi = GAMES.get(game_id)
    if not gi:
        raise HTTPException(404, "Game not found")
    state = gi.game.get_full_state()
    state["game_id"] = game_id
    state["diplo_log"] = gi.diplo_log
    state["turn_log"] = gi.turn_log
    return state

@app.post("/games/{game_id}/diplomacy")
def submit_diplomacy(game_id: str, req: SubmitDiplomacyRequest, authorization: str = Header(...)):
    gi, pid = get_player(game_id, authorization)
    if gi.game.winner:
        raise HTTPException(400, "Game over")
    for msg in req.messages:
        gi.diplo_log.append({
            "turn": gi.game.turn, "from": pid, "to": msg.to,
            "content": msg.content, "ts": time.time(),
        })
    return {"ok": True}

@app.post("/games/{game_id}/orders")
def submit_orders(game_id: str, req: SubmitOrdersRequest, authorization: str = Header(...)):
    gi, pid = get_player(game_id, authorization)
    if gi.game.winner:
        raise HTTPException(400, "Game over")
    if not gi.game.players[pid].alive:
        raise HTTPException(400, "Eliminated")

    orders = Orders(player_id=pid)
    for m in req.moves:
        orders.moves.append(MoveOrder(unit_id=m["unit_id"], target=m["target"]))
    for b in req.build_units:
        orders.build_units.append(BuildUnitOrder(unit_type=b["type"], province=b["province"]))
    for b in req.build_buildings:
        orders.build_buildings.append(BuildBuildingOrder(building_type=b["type"], province=b["province"]))
    if req.research:
        orders.research = ResearchOrder(tech=req.research["tech"])
    for tr in req.trade_routes:
        orders.trade_routes.append(TradeRouteOrder(from_province=tr["from"], to_province=tr["to"]))

    gi.pending_orders[pid] = orders

    alive = [p for p in gi.game.players if gi.game.players[p].alive]
    if set(alive) <= set(gi.pending_orders.keys()):
        return _process_turn(gi)
    return {"status": "waiting", "submitted": list(gi.pending_orders.keys()),
            "need": [p for p in alive if p not in gi.pending_orders]}

@app.post("/games/{game_id}/process")
def force_process(game_id: str):
    gi = GAMES.get(game_id)
    if not gi:
        raise HTTPException(404)
    if gi.game.winner:
        raise HTTPException(400, "Game over")
    for pid in gi.game.players:
        if gi.game.players[pid].alive and pid not in gi.pending_orders:
            gi.pending_orders[pid] = Orders(player_id=pid)
    return _process_turn(gi)

def _process_turn(gi: GameInstance) -> dict:
    result = gi.game.process_turn(gi.pending_orders)
    gi.turn_log.append({
        "turn": result.turn,
        "events": result.events,
        "combats": [{"p": c.province, "w": c.winner, "s": c.sides, "l": c.losses} for c in result.combats],
        "income": result.income,
        "eliminations": result.eliminations,
        "winner": result.winner,
        "state": gi.game.get_full_state(),
    })
    gi.pending_orders.clear()
    if gi.game.winner:
        _save_replay(gi)
    return {
        "status": "turn_processed", "turn": result.turn,
        "combats": len(result.combats), "eliminations": result.eliminations,
        "winner": result.winner, "events": result.events,
    }

def _save_replay(gi: GameInstance):
    replay = {"game_id": gi.id, "players": list(gi.game.players.keys()),
              "winner": gi.game.winner, "turns": gi.turn_log, "diplomacy": gi.diplo_log}
    (REPLAY_DIR / f"{gi.id}.json").write_text(json.dumps(replay))

@app.get("/games/{game_id}/replay")
def get_replay(game_id: str):
    gi = GAMES.get(game_id)
    if gi:
        return {"game_id": gi.id, "players": list(gi.game.players.keys()),
                "winner": gi.game.winner, "turns": gi.turn_log, "diplomacy": gi.diplo_log}
    path = REPLAY_DIR / f"{game_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    raise HTTPException(404)

@app.get("/games")
def list_games():
    return [{"game_id": gid, "turn": gi.game.turn, "winner": gi.game.winner,
             "players": len(gi.game.players)} for gid, gi in GAMES.items()]

# Serve frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    @app.get("/")
    def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
