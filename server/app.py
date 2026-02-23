"""Stratagem Game Server — FastAPI."""
from __future__ import annotations
import json, os, time, uuid, secrets
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.game import Game
from src.types import Orders, MoveOrder, BuildUnitOrder, BuildBuildingOrder, UnitType, BuildingType

app = FastAPI(title="Stratagem", version="0.1.0")

# ── Data stores ──────────────────────────────────────────────────────────────

@dataclass
class GameInstance:
    id: str
    game: Game
    player_keys: dict[str, str]  # player_id -> api_key
    spectator_key: str
    pending_orders: dict[str, Orders] = field(default_factory=dict)
    pending_diplo: dict[str, list[dict]] = field(default_factory=dict)
    diplo_log: list[dict] = field(default_factory=list)
    turn_log: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    auto_process: bool = True  # process turn when all orders received

GAMES: dict[str, GameInstance] = {}
REPLAY_DIR = Path(__file__).resolve().parent.parent / "replays"
REPLAY_DIR.mkdir(exist_ok=True)

# ── Auth helpers ─────────────────────────────────────────────────────────────

def get_player(game_id: str, authorization: str = Header(...)) -> tuple[GameInstance, str]:
    token = authorization.replace("Bearer ", "")
    gi = GAMES.get(game_id)
    if not gi:
        raise HTTPException(404, "Game not found")
    for pid, key in gi.player_keys.items():
        if key == token:
            return gi, pid
    raise HTTPException(403, "Invalid API key")

def get_spectator(game_id: str, authorization: str = Header(...)) -> GameInstance:
    token = authorization.replace("Bearer ", "")
    gi = GAMES.get(game_id)
    if not gi:
        raise HTTPException(404, "Game not found")
    if token != gi.spectator_key:
        # Also allow player keys for spectating
        if token not in gi.player_keys.values():
            raise HTTPException(403, "Invalid key")
    return gi

# ── Models ───────────────────────────────────────────────────────────────────

class CreateGameRequest(BaseModel):
    num_players: int = 4
    num_provinces: int = 20
    seed: int | None = None
    max_turns: int = 40

class MoveOrderModel(BaseModel):
    unit_id: str
    target_province: str

class BuildUnitModel(BaseModel):
    unit_type: str
    province: str

class BuildBuildingModel(BaseModel):
    building_type: str
    province: str

class SubmitOrdersRequest(BaseModel):
    moves: list[MoveOrderModel] = []
    build_units: list[BuildUnitModel] = []
    build_buildings: list[BuildBuildingModel] = []

class DiplomacyMessage(BaseModel):
    to: str  # player_id or "public"
    content: str

class SubmitDiplomacyRequest(BaseModel):
    messages: list[DiplomacyMessage] = []

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/games")
def create_game(req: CreateGameRequest):
    gid = str(uuid.uuid4())[:8]
    game = Game.create(num_players=req.num_players, num_provinces=req.num_provinces, seed=req.seed)
    game.max_turns = req.max_turns
    
    player_keys = {}
    for pid in game.players:
        player_keys[pid] = secrets.token_hex(16)
    
    spectator_key = secrets.token_hex(16)
    
    gi = GameInstance(id=gid, game=game, player_keys=player_keys, spectator_key=spectator_key)
    GAMES[gid] = gi
    
    # Log initial state
    gi.turn_log.append({"turn": 0, "event": "game_created", "state": game.get_full_state()})
    
    return {
        "game_id": gid,
        "player_keys": player_keys,
        "spectator_key": spectator_key,
        "players": list(game.players.keys()),
        "provinces": len(game.provinces),
    }

@app.get("/games/{game_id}/state")
def get_state(game_id: str, authorization: str = Header(...)):
    gi, pid = get_player(game_id, authorization)
    state = gi.game.get_state_for_player(pid)
    state["pending_diplomacy"] = [
        m for m in gi.diplo_log
        if m["turn"] == gi.game.turn and (m["to"] == pid or m["to"] == "public")
    ]
    state["game_id"] = game_id
    state["winner"] = gi.game.winner
    state["phase"] = "orders"  # simplified — always accepting orders
    return state

@app.get("/games/{game_id}/spectator")
def get_spectator_state(game_id: str, authorization: str = Header(default="")):
    gi = GAMES.get(game_id)
    if not gi:
        raise HTTPException(404, "Game not found")
    # Allow unauthenticated spectating for simplicity in frontend
    state = gi.game.get_full_state()
    state["game_id"] = game_id
    state["winner"] = gi.game.winner
    state["diplo_log"] = gi.diplo_log
    state["turn_log"] = gi.turn_log
    return state

@app.post("/games/{game_id}/diplomacy")
def submit_diplomacy(game_id: str, req: SubmitDiplomacyRequest, authorization: str = Header(...)):
    gi, pid = get_player(game_id, authorization)
    if gi.game.winner:
        raise HTTPException(400, "Game is over")
    
    for msg in req.messages:
        entry = {
            "turn": gi.game.turn,
            "from": pid,
            "to": msg.to,
            "content": msg.content,
            "timestamp": time.time(),
        }
        gi.diplo_log.append(entry)
    
    return {"status": "ok", "messages_sent": len(req.messages)}

@app.post("/games/{game_id}/orders")
def submit_orders(game_id: str, req: SubmitOrdersRequest, authorization: str = Header(...)):
    gi, pid = get_player(game_id, authorization)
    if gi.game.winner:
        raise HTTPException(400, "Game is over")
    if not gi.game.players[pid].alive:
        raise HTTPException(400, "Player is eliminated")
    
    orders = Orders(player_id=pid)
    for m in req.moves:
        orders.moves.append(MoveOrder(unit_id=m.unit_id, target_province=m.target_province))
    for b in req.build_units:
        orders.build_units.append(BuildUnitOrder(unit_type=UnitType(b.unit_type), province=b.province))
    for b in req.build_buildings:
        orders.build_buildings.append(BuildBuildingOrder(building_type=BuildingType(b.building_type), province=b.province))
    
    gi.pending_orders[pid] = orders
    
    # Auto-process when all alive players have submitted
    alive_players = [p for p in gi.game.players if gi.game.players[p].alive]
    if gi.auto_process and set(alive_players) <= set(gi.pending_orders.keys()):
        return _process_turn(gi)
    
    return {"status": "waiting", "submitted": list(gi.pending_orders.keys()), "waiting_for": [p for p in alive_players if p not in gi.pending_orders]}

@app.post("/games/{game_id}/process")
def force_process(game_id: str, authorization: str = Header(default="")):
    """Force process the current turn (for testing)."""
    gi = GAMES.get(game_id)
    if not gi:
        raise HTTPException(404, "Game not found")
    if gi.game.winner:
        raise HTTPException(400, "Game is over")
    
    # Fill in empty orders for players who haven't submitted
    for pid in gi.game.players:
        if gi.game.players[pid].alive and pid not in gi.pending_orders:
            gi.pending_orders[pid] = Orders(player_id=pid)
    
    return _process_turn(gi)

def _process_turn(gi: GameInstance) -> dict:
    result = gi.game.process_turn(gi.pending_orders)
    
    # Log
    log_entry = {
        "turn": result.turn,
        "combats": [{"province": c.province, "attackers": c.attackers, "winner": c.winner, "losses": c.losses} for c in result.combats],
        "resources": result.resources_collected,
        "eliminations": result.eliminations,
        "winner": result.winner,
        "state": gi.game.get_full_state(),
    }
    gi.turn_log.append(log_entry)
    gi.pending_orders.clear()
    
    # Save replay on game end
    if gi.game.winner:
        _save_replay(gi)
    
    return {
        "status": "turn_processed",
        "turn": result.turn,
        "combats": len(result.combats),
        "eliminations": result.eliminations,
        "winner": result.winner,
    }

def _save_replay(gi: GameInstance):
    replay = {
        "game_id": gi.id,
        "created_at": gi.created_at,
        "players": list(gi.game.players.keys()),
        "winner": gi.game.winner,
        "turns": gi.turn_log,
        "diplomacy": gi.diplo_log,
    }
    path = REPLAY_DIR / f"{gi.id}.json"
    path.write_text(json.dumps(replay, indent=2))

@app.get("/games/{game_id}/replay")
def get_replay(game_id: str):
    gi = GAMES.get(game_id)
    if not gi:
        # Check file
        path = REPLAY_DIR / f"{game_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        raise HTTPException(404, "Game not found")
    return {
        "game_id": gi.id,
        "players": list(gi.game.players.keys()),
        "winner": gi.game.winner,
        "turns": gi.turn_log,
        "diplomacy": gi.diplo_log,
    }

@app.get("/games")
def list_games():
    return [{
        "game_id": gid,
        "turn": gi.game.turn,
        "winner": gi.game.winner,
        "players": len(gi.game.players),
    } for gid, gi in GAMES.items()]

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
