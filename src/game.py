"""Core game engine for Stratagem."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from .types import (
    Province, Player, Unit, UnitType, Building, BuildingType,
    Orders, MoveOrder, BuildUnitOrder, BuildBuildingOrder,
    CombatResult, TurnResult, UNIT_STATS, TERRAIN_DEFENSE_BONUS,
)
from .map_gen import generate_map


@dataclass
class Game:
    provinces: dict[str, Province]
    players: dict[str, Player]
    turn: int = 0
    history: list[TurnResult] = field(default_factory=list)
    winner: str | None = None
    max_turns: int = 40
    domination_threshold: float = 0.6
    domination_counter: dict[str, int] = field(default_factory=dict)

    @classmethod
    def create(cls, num_players: int = 4, num_provinces: int = 25, seed: int | None = None) -> Game:
        provinces = generate_map(num_provinces, num_players, seed)
        players = {}
        for i in range(num_players):
            pid = f"player_{i}"
            players[pid] = Player(id=pid, name=pid)
        return cls(provinces=provinces, players=players)

    def get_player_provinces(self, player_id: str) -> list[Province]:
        return [p for p in self.provinces.values() if p.owner == player_id]

    def get_player_units(self, player_id: str) -> list[Unit]:
        units = []
        for p in self.provinces.values():
            for u in p.units:
                if u.owner == player_id:
                    units.append(u)
        return units

    def collect_resources(self) -> dict[str, dict[str, int]]:
        """Collect resources for all players."""
        collected = {}
        for pid, player in self.players.items():
            if not player.alive:
                continue
            income = {"food": 0, "iron": 0, "gold": 0}
            for prov in self.get_player_provinces(pid):
                prod = prov.resource_production()
                for r, v in prod.items():
                    income[r] = income.get(r, 0) + v
            # Upkeep: 1 food per non-militia unit
            upkeep = sum(1 for u in self.get_player_units(pid) if u.type != UnitType.MILITIA)
            income["food"] -= upkeep
            for r, v in income.items():
                player.resources[r] = player.resources.get(r, 0) + v
                player.resources[r] = max(0, player.resources[r])
            collected[pid] = income
        return collected

    def process_moves(self, all_orders: dict[str, Orders]) -> list[CombatResult]:
        """Process all move orders simultaneously, then resolve combat."""
        combats = []
        
        # Execute moves
        for pid, orders in all_orders.items():
            for move in orders.moves:
                unit = self._find_unit(move.unit_id)
                if unit is None or unit.owner != pid:
                    continue
                src = self.provinces.get(unit.province)
                dst = self.provinces.get(move.target_province)
                if src is None or dst is None:
                    continue
                if dst.id not in src.adjacent:
                    continue
                # Move unit
                src.units.remove(unit)
                unit.province = dst.id
                dst.units.append(unit)
        
        # Resolve combat in provinces with multiple owners' units
        for prov in self.provinces.values():
            owners_in_province = set(u.owner for u in prov.units)
            if len(owners_in_province) <= 1:
                continue
            combat = self._resolve_combat(prov)
            if combat:
                combats.append(combat)
        
        return combats

    def _resolve_combat(self, prov: Province) -> CombatResult | None:
        """Resolve combat in a province. Defender gets terrain bonus."""
        owners = {}
        for u in prov.units:
            if u.owner not in owners:
                owners[u.owner] = []
            owners[u.owner].append(u)
        
        if len(owners) < 2:
            return None
        
        # Calculate strength per player
        strengths = {}
        for pid, units in owners.items():
            s = sum(u.strength for u in units)
            if pid == prov.owner:
                s += prov.defense_bonus
            strengths[pid] = s
        
        # Winner is highest strength (ties favor defender)
        sorted_players = sorted(strengths.items(), key=lambda x: (-x[1], x[0] != prov.owner))
        winner = sorted_players[0][0]
        
        # Losers lose all units in this province
        losses = {}
        for pid, units in owners.items():
            if pid != winner:
                losses[pid] = len(units)
                prov.units = [u for u in prov.units if u.owner != pid]
        
        # Winner loses proportional units (simplified: lose 1 unit per 3 strength of losers)
        loser_total = sum(strengths[p] for p in losses)
        winner_casualties = loser_total // 5
        winner_units = [u for u in prov.units if u.owner == winner]
        for i in range(min(winner_casualties, len(winner_units) - 1)):  # always keep at least 1
            prov.units.remove(winner_units[i])
            losses[winner] = losses.get(winner, 0) + 1
        
        # Province ownership changes
        prov.owner = winner
        
        return CombatResult(
            province=prov.id,
            attackers=strengths,
            winner=winner,
            losses=losses,
        )

    def process_builds(self, all_orders: dict[str, Orders]):
        """Process build orders."""
        for pid, orders in all_orders.items():
            player = self.players[pid]
            if not player.alive:
                continue
            
            for build in orders.build_units:
                prov = self.provinces.get(build.province)
                if prov is None or prov.owner != pid:
                    continue
                cost, _, _ = UNIT_STATS[build.unit_type]
                if not self._can_afford(player, cost):
                    continue
                self._pay(player, cost)
                uid = f"{pid}_{build.unit_type.value}_{self.turn}_{len(prov.units)}"
                prov.units.append(Unit(
                    id=uid, type=build.unit_type, owner=pid, province=prov.id
                ))
            
            for build in orders.build_buildings:
                prov = self.provinces.get(build.province)
                if prov is None or prov.owner != pid:
                    continue
                # Simplified costs
                costs = {
                    BuildingType.FARM: {"food": 2},
                    BuildingType.MINE: {"iron": 2},
                    BuildingType.MARKET: {"gold": 3},
                    BuildingType.FORTRESS: {"iron": 3, "gold": 2},
                    BuildingType.BARRACKS: {"iron": 2},
                    BuildingType.WATCHTOWER: {"iron": 1, "gold": 1},
                    BuildingType.EMBASSY: {"gold": 3},
                }
                cost = costs.get(build.building_type, {})
                if not self._can_afford(player, cost):
                    continue
                self._pay(player, cost)
                prov.buildings.append(Building(type=build.building_type, turns_remaining=1))

    def advance_buildings(self):
        """Tick building construction."""
        for prov in self.provinces.values():
            for b in prov.buildings:
                if b.turns_remaining > 0:
                    b.turns_remaining -= 1

    def check_victory(self) -> str | None:
        """Check win conditions."""
        alive_players = [p for p in self.players.values() if p.alive]
        
        # Last standing
        if len(alive_players) == 1:
            return alive_players[0].id
        
        # Domination
        total = len(self.provinces)
        for p in alive_players:
            owned = len(self.get_player_provinces(p.id))
            if owned / total >= self.domination_threshold:
                self.domination_counter[p.id] = self.domination_counter.get(p.id, 0) + 1
                if self.domination_counter[p.id] >= 3:
                    return p.id
            else:
                self.domination_counter[p.id] = 0
        
        # Score victory at max turns
        if self.turn >= self.max_turns:
            scores = {}
            for p in alive_players:
                provs = len(self.get_player_provinces(p.id))
                units = len(self.get_player_units(p.id))
                gold = p.resources.get("gold", 0)
                scores[p.id] = provs * 2 + units + gold // 5
            return max(scores, key=scores.get)
        
        return None

    def check_eliminations(self) -> list[str]:
        """Eliminate players with no provinces and no units."""
        eliminated = []
        for pid, player in self.players.items():
            if not player.alive:
                continue
            if not self.get_player_provinces(pid) and not self.get_player_units(pid):
                player.alive = False
                eliminated.append(pid)
        return eliminated

    def process_turn(self, all_orders: dict[str, Orders]) -> TurnResult:
        """Process a complete turn."""
        self.turn += 1
        result = TurnResult(turn=self.turn)
        
        # 1. Process moves and combat
        result.combats = self.process_moves(all_orders)
        
        # 2. Process builds
        self.process_builds(all_orders)
        
        # 3. Advance building construction
        self.advance_buildings()
        
        # 4. Collect resources
        result.resources_collected = self.collect_resources()
        
        # 5. Check eliminations
        result.eliminations = self.check_eliminations()
        
        # 6. Check victory
        result.winner = self.check_victory()
        if result.winner:
            self.winner = result.winner
        
        self.history.append(result)
        return result

    def get_state_for_player(self, player_id: str) -> dict:
        """Get the game state from a specific player's perspective (fog of war)."""
        player = self.players[player_id]
        owned = self.get_player_provinces(player_id)
        owned_ids = {p.id for p in owned}
        
        # Visible = owned + adjacent to owned
        visible_ids = set(owned_ids)
        for p in owned:
            visible_ids.update(p.adjacent)
        
        visible = {}
        for pid in visible_ids:
            prov = self.provinces[pid]
            if pid in owned_ids:
                # Full info
                visible[pid] = {
                    "name": prov.name, "terrain": prov.terrain.value,
                    "owner": prov.owner,
                    "units": [{"id": u.id, "type": u.type.value, "owner": u.owner} for u in prov.units],
                    "buildings": [{"type": b.type.value, "done": b.turns_remaining == 0} for b in prov.buildings],
                    "production": prov.resource_production(),
                    "adjacent": prov.adjacent,
                }
            else:
                # Partial info — terrain, owner, no unit details
                visible[pid] = {
                    "name": prov.name, "terrain": prov.terrain.value,
                    "owner": prov.owner,
                    "adjacent": prov.adjacent,
                }
        
        fog = [pid for pid in self.provinces if pid not in visible_ids]
        
        return {
            "turn": self.turn,
            "player": player_id,
            "resources": player.resources,
            "provinces": visible,
            "fog": fog,
        }

    def get_full_state(self) -> dict:
        """Full state for spectators."""
        return {
            "turn": self.turn,
            "players": {pid: {"resources": p.resources, "alive": p.alive} for pid, p in self.players.items()},
            "provinces": {
                pid: {
                    "name": prov.name, "terrain": prov.terrain.value, "owner": prov.owner,
                    "units": len(prov.units),
                    "unit_strength": sum(u.strength for u in prov.units),
                }
                for pid, prov in self.provinces.items()
            },
        }

    def _find_unit(self, unit_id: str) -> Unit | None:
        for prov in self.provinces.values():
            for u in prov.units:
                if u.id == unit_id:
                    return u
        return None

    def _can_afford(self, player: Player, cost: dict[str, int]) -> bool:
        return all(player.resources.get(r, 0) >= v for r, v in cost.items())

    def _pay(self, player: Player, cost: dict[str, int]):
        for r, v in cost.items():
            player.resources[r] -= v
