"""ELO Rankings & Match History for Stratagem."""
from __future__ import annotations
import json, time, uuid, math
from pathlib import Path
from dataclasses import dataclass, field, asdict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
RANKINGS_FILE = DATA_DIR / "rankings.json"
MATCHES_FILE = DATA_DIR / "matches.json"

K_FACTOR = 32
STARTING_RATING = 1000


@dataclass
class AgentProfile:
    agent_id: str
    rating: int = STARTING_RATING
    peak_rating: int = STARTING_RATING
    wins: int = 0
    losses: int = 0
    draws: int = 0
    games_played: int = 0
    rating_history: list[dict] = field(default_factory=list)

    def win_rate(self) -> float:
        return self.wins / self.games_played if self.games_played else 0.0


@dataclass
class MatchRecord:
    match_id: str
    players: list[str]
    placements: list[str]  # ordered 1st, 2nd, 3rd...
    winner: str | None
    turn_count: int
    date: str  # ISO format
    replay_file: str | None = None


def _load_rankings() -> dict[str, AgentProfile]:
    if RANKINGS_FILE.exists():
        data = json.loads(RANKINGS_FILE.read_text())
        return {k: AgentProfile(**v) for k, v in data.items()}
    return {}


def _save_rankings(rankings: dict[str, AgentProfile]):
    DATA_DIR.mkdir(exist_ok=True)
    RANKINGS_FILE.write_text(json.dumps({k: asdict(v) for k, v in rankings.items()}, indent=2))


def _load_matches() -> list[MatchRecord]:
    if MATCHES_FILE.exists():
        data = json.loads(MATCHES_FILE.read_text())
        return [MatchRecord(**m) for m in data]
    return []


def _save_matches(matches: list[MatchRecord]):
    DATA_DIR.mkdir(exist_ok=True)
    MATCHES_FILE.write_text(json.dumps([asdict(m) for m in matches], indent=2))


def get_or_create_profile(agent_id: str) -> AgentProfile:
    rankings = _load_rankings()
    if agent_id not in rankings:
        rankings[agent_id] = AgentProfile(agent_id=agent_id)
        _save_rankings(rankings)
    return rankings[agent_id]


def _expected_score(ra: int, rb: int) -> float:
    return 1.0 / (1.0 + math.pow(10, (rb - ra) / 400.0))


def update_multiplayer_elo(placements: list[str]) -> dict[str, int]:
    """
    Multiplayer ELO: each player plays a 'virtual match' against every other player.
    Placement determines win/loss: higher placement = win over lower placement.
    Returns dict of {agent_id: new_rating}.
    """
    rankings = _load_rankings()
    n = len(placements)

    # Ensure all players exist
    for pid in placements:
        if pid not in rankings:
            rankings[pid] = AgentProfile(agent_id=pid)

    ratings = {pid: rankings[pid].rating for pid in placements}
    new_ratings = {}

    for i, pid in enumerate(placements):
        ra = ratings[pid]
        total_expected = 0.0
        total_actual = 0.0

        for j, opp in enumerate(placements):
            if i == j:
                continue
            total_expected += _expected_score(ra, ratings[opp])
            if i < j:
                total_actual += 1.0  # win
            elif i == j:
                total_actual += 0.5  # draw
            # else: loss (0)

        adjustment = K_FACTOR * (total_actual - total_expected) / (n - 1)
        new_ratings[pid] = max(100, round(ra + adjustment))

    # Update profiles
    for pid in placements:
        p = rankings[pid]
        p.rating = new_ratings[pid]
        p.peak_rating = max(p.peak_rating, p.rating)
        p.games_played += 1
        p.rating_history.append({"rating": p.rating, "time": time.time()})

    # Win/loss tracking
    if placements:
        rankings[placements[0]].wins += 1
        for pid in placements[1:]:
            rankings[pid].losses += 1

    _save_rankings(rankings)
    return new_ratings


def record_match(
    players: list[str],
    placements: list[str],
    winner: str | None,
    turn_count: int,
    replay_file: str | None = None,
) -> MatchRecord:
    matches = _load_matches()
    record = MatchRecord(
        match_id=str(uuid.uuid4())[:8],
        players=players,
        placements=placements,
        winner=winner,
        turn_count=turn_count,
        date=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        replay_file=replay_file,
    )
    matches.append(record)
    _save_matches(matches)

    # Update ELO
    update_multiplayer_elo(placements)

    return record


def get_leaderboard(limit: int = 50) -> list[dict]:
    rankings = _load_rankings()
    sorted_profiles = sorted(rankings.values(), key=lambda p: p.rating, reverse=True)
    return [asdict(p) for p in sorted_profiles[:limit]]


def get_agent_profile(agent_id: str) -> dict | None:
    rankings = _load_rankings()
    p = rankings.get(agent_id)
    return asdict(p) if p else None


def get_matches(limit: int = 50, offset: int = 0) -> list[dict]:
    matches = _load_matches()
    matches.reverse()  # newest first
    return [asdict(m) for m in matches[offset:offset + limit]]


def get_match(match_id: str) -> dict | None:
    for m in _load_matches():
        if m.match_id == match_id:
            return asdict(m)
    return None
