"""Core game engine for Stratagem v2."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from .types import (
    Province, Player, Unit, UnitType, Building, BuildingType, TechId,
    Orders, MoveOrder, BuildUnitOrder, BuildBuildingOrder, ResearchOrder,
    TradeRoute, TradeRouteOrder, CombatResult, TurnResult,
    DiplomacyMessage, TreatyProposal, Treaty, TreatyType, DiplomacyOrder,
    UNIT_STATS, UNIT_ORDER, TERRAIN_DEFENSE, TERRAIN_SHORT,
    BUILDING_SHORT, BUILDING_STATS, TRIANGLE, TERRAIN_UNIT_BONUS,
    CIV_UNIQUE_UNIT, AGE_COST, TECH_COST, TECH_AGE, TECH_GROUPS,
)
from .map_gen import generate_map, CIVS, PLAYER_STARTS
from .tech import can_research


@dataclass
class Game:
    provinces: dict[str, Province]
    players: dict[str, Player]
    trade_routes: list[TradeRoute] = field(default_factory=list)
    messages: list[DiplomacyMessage] = field(default_factory=list)
    treaties: list[Treaty] = field(default_factory=list)
    proposals: list[TreatyProposal] = field(default_factory=list)
    trust_penalties: dict[str, int] = field(default_factory=dict)  # pid -> broken treaty count
    turn: int = 0
    history: list[TurnResult] = field(default_factory=list)
    winner: str | None = None
    max_turns: int = 40
    _uid: int = 0  # unit id counter
    _treaty_uid: int = 0

    def _next_uid(self, player_id: str, utype: str) -> str:
        self._uid += 1
        return f"{player_id}_{utype}_{self._uid}"

    @classmethod
    def create(cls, num_players: int = 4, seed: int | None = None,
               civs: list[str] | None = None) -> Game:
        provinces = generate_map(num_players, seed)
        players = {}
        civ_list = civs or CIVS[:num_players]
        for i in range(num_players):
            pid = f"p{i}"
            players[pid] = Player(id=pid, name=pid, civ=civ_list[i % len(civ_list)])
        return cls(provinces=provinces, players=players)

    # ── Queries ──────────────────────────────────────────────────────────

    def player_provinces(self, pid: str) -> list[Province]:
        return [p for p in self.provinces.values() if p.owner == pid]

    def player_units(self, pid: str) -> list[Unit]:
        return [u for p in self.provinces.values() for u in p.units if u.owner == pid]

    # ── Resource Collection ──────────────────────────────────────────────

    def collect_resources(self) -> dict[str, list[int]]:
        collected = {}
        for pid, player in self.players.items():
            if not player.alive:
                continue
            inc = [0, 0, 0]
            for prov in self.player_provinces(pid):
                f, i, g = prov.production(player.techs)
                # Verdanti bonus: +1 food from all provinces
                if player.civ == "verdanti":
                    f += 1
                # Unique unit bonuses in this province
                for u in prov.units:
                    if u.owner == pid:
                        if u.type == UnitType.SAGE:
                            # Ashwalker sage: +1 all resources per sage
                            f += 1; i += 1; g += 1
                        elif u.type == UnitType.HERBALIST:
                            # Verdanti herbalist: +2 food per herbalist
                            f += 2
                inc[0] += f; inc[1] += i; inc[2] += g

            # Upkeep: 1 food per non-militia, non-scout unit
            upkeep = sum(1 for u in self.player_units(pid)
                         if u.type not in (UnitType.MILITIA, UnitType.SCOUT))
            inc[0] -= upkeep

            # Trade route income
            trade_gold = self._calc_trade_income(pid)
            inc[2] += trade_gold

            for j in range(3):
                player.resources[j] = max(0, player.resources[j] + inc[j])
            collected[pid] = inc
        return collected

    def _calc_trade_income(self, pid: str) -> int:
        total = 0
        for tr in self.trade_routes:
            if tr.owner != pid and tr.partner != pid:
                continue
            # Calculate distance (BFS shortest path length)
            dist = self._bfs_dist(tr.from_province, tr.to_province)
            if dist <= 0:
                continue
            base_income = dist
            # Check if route is raided (enemy units on path)
            raided = self._is_route_raided(tr, pid)
            if raided:
                base_income = base_income // 2
            # Tidecaller bonus
            player = self.players[pid]
            if player.civ == "tidecallers":
                base_income = base_income * 3 // 2
            # Shared routes give income to both
            if tr.partner and tr.partner != tr.owner:
                base_income = base_income * 2  # double but split
                if pid == tr.owner or pid == tr.partner:
                    base_income = base_income // 2
            tr.income = base_income
            total += base_income
        return total

    def _bfs_dist(self, a: str, b: str) -> int:
        if a == b: return 0
        visited = {a}
        queue = [(a, 0)]
        while queue:
            node, d = queue.pop(0)
            for nb in self.provinces[node].adjacent:
                if nb == b:
                    return d + 1
                if nb not in visited:
                    visited.add(nb)
                    queue.append((nb, d + 1))
        return -1

    def _is_route_raided(self, tr: TradeRoute, pid: str) -> bool:
        """Check if any province on shortest path has enemy units."""
        path = self._bfs_path(tr.from_province, tr.to_province)
        for prov_id in path[1:-1]:  # exclude endpoints
            prov = self.provinces[prov_id]
            for u in prov.units:
                if u.owner != pid and u.owner != tr.partner:
                    return True
        return False

    def _bfs_path(self, a: str, b: str) -> list[str]:
        if a == b: return [a]
        visited = {a}
        queue = [(a, [a])]
        while queue:
            node, path = queue.pop(0)
            for nb in self.provinces[node].adjacent:
                if nb == b:
                    return path + [b]
                if nb not in visited:
                    visited.add(nb)
                    queue.append((nb, path + [nb]))
        return []

    # ── Movement & Combat ────────────────────────────────────────────────

    def process_moves(self, all_orders: dict[str, Orders], events: list[str]) -> list[CombatResult]:
        combats = []

        # Execute moves
        for pid, orders in all_orders.items():
            player = self.players[pid]
            for move in orders.moves:
                unit = self._find_unit(move.unit_id)
                if not unit or unit.owner != pid:
                    continue
                src = self.provinces.get(unit.province)
                dst = self.provinces.get(move.target)
                if not src or not dst or dst.id not in src.adjacent:
                    continue
                # Speed check (speed >= 1 means can move 1 province)
                src.units.remove(unit)
                unit.province = dst.id
                dst.units.append(unit)

        # Resolve combat
        for prov in self.provinces.values():
            owners = set(u.owner for u in prov.units)
            if len(owners) <= 1:
                continue
            combat = self._resolve_combat(prov, events)
            if combat:
                combats.append(combat)
        return combats

    def _resolve_combat(self, prov: Province, events: list[str]) -> CombatResult | None:
        owners: dict[str, list[Unit]] = {}
        for u in prov.units:
            owners.setdefault(u.owner, []).append(u)
        if len(owners) < 2:
            return None

        # Calculate effective strength per side
        strengths: dict[str, float] = {}
        for pid, units in owners.items():
            s = 0.0
            player = self.players[pid]
            for u in units:
                us = u.strength
                # Tactics tech: +1 str
                if TechId.TACTICS in player.techs:
                    us += 1
                # Triangle bonuses against enemy unit types
                enemy_types = set()
                for opid, ounits in owners.items():
                    if opid != pid:
                        enemy_types.update(ou.type for ou in ounits)
                if u.type in TRIANGLE:
                    for et in enemy_types:
                        us += TRIANGLE[u.type].get(et, 0)
                # Terrain bonus
                if u.type in TERRAIN_UNIT_BONUS:
                    us += TERRAIN_UNIT_BONUS[u.type].get(prov.terrain, 0)
                # Huscarl: immune to archer bonus
                if u.type.value == "infantry" and player.civ == "ironborn":
                    pass  # normal, huscarl handled separately
                s += us
            # Defender bonus
            if pid == prov.owner:
                s += prov.defense_bonus
                if TechId.FORTIFICATION in player.techs:
                    s += 1
            # River terrain: attackers -1 per unit
            if prov.terrain.value == "river" and pid != prov.owner:
                s -= len(units)
                s = max(s, 0)
            strengths[pid] = s

        # Winner = highest strength (ties favor defender, then alphabetical)
        sorted_sides = sorted(strengths.items(),
                              key=lambda x: (-x[1], x[0] != prov.owner, x[0]))
        winner = sorted_sides[0][0]

        losses: dict[str, int] = {}
        # Losers lose all units
        for pid in list(owners.keys()):
            if pid != winner:
                losses[pid] = len(owners[pid])
                prov.units = [u for u in prov.units if u.owner != pid]

        # Winner casualties: floor(loser_total_str / 4), remove weakest first
        loser_str = sum(strengths[p] for p in losses)
        winner_casualties = int(loser_str // 4)
        winner_units = sorted([u for u in prov.units if u.owner == winner],
                              key=lambda u: u.strength)
        for i in range(min(winner_casualties, max(0, len(winner_units) - 1))):
            prov.units.remove(winner_units[i])
            losses[winner] = losses.get(winner, 0) + 1

        # Veterancy: surviving winner units gain +1 (max +2)
        for u in prov.units:
            if u.owner == winner and u.veteran < 2:
                u.veteran += 1

        # Corsair gold capture: 2 gold per kill if corsairs participated
        winner_corsairs = sum(1 for u in prov.units if u.owner == winner and u.type == UnitType.CORSAIR)
        if winner_corsairs > 0:
            total_killed = sum(v for k, v in losses.items() if k != winner)
            gold_gain = total_killed * 2
            self.players[winner].resources[2] += gold_gain

        prov.owner = winner
        events.append(f"⚔️ Battle at {prov.name}: {winner} wins (str {strengths[winner]:.0f} vs {', '.join(f'{p}:{s:.0f}' for p,s in strengths.items() if p!=winner)})")

        return CombatResult(
            province=prov.id, sides={p: int(s) for p, s in strengths.items()},
            winner=winner, losses=losses,
        )

    # ── Building ─────────────────────────────────────────────────────────

    def process_builds(self, all_orders: dict[str, Orders], events: list[str]):
        for pid, orders in all_orders.items():
            player = self.players[pid]
            if not player.alive:
                continue

            # Build units
            for build in orders.build_units:
                prov = self.provinces.get(build.province)
                if not prov or prov.owner != pid:
                    continue

                if build.unit_type == "unique":
                    # Unique unit — resolve to civ-specific type
                    if player.civ not in CIV_UNIQUE_UNIT:
                        continue
                    utype = CIV_UNIQUE_UNIT[player.civ]
                    stats = UNIT_STATS[utype]
                    if player.age < stats[3]:
                        continue
                    cost = player.civ_unit_discount(stats[0])
                    if not player.can_afford(cost):
                        continue
                    player.pay(cost)
                    uid = self._next_uid(pid, utype.value)
                    u = Unit(id=uid, type=utype, owner=pid, province=prov.id)
                    prov.units.append(u)
                    events.append(f"🏗️ {pid} built {utype.value} at {prov.name}")
                    continue

                try:
                    utype = UnitType(build.unit_type)
                except ValueError:
                    continue
                stats = UNIT_STATS[utype]
                if player.age < stats[3]:  # min_age check
                    continue
                cost = player.civ_unit_discount(stats[0])
                # Barracks discount
                if prov.has_building(BuildingType.BARRACKS):
                    cost = (max(0, cost[0] - 1), cost[1], cost[2])
                if not player.can_afford(cost):
                    continue
                player.pay(cost)
                uid = self._next_uid(pid, utype.value)
                prov.units.append(Unit(id=uid, type=utype, owner=pid, province=prov.id))
                events.append(f"🏗️ {pid} built {utype.value} at {prov.name}")

            # Build buildings
            for build in orders.build_buildings:
                prov = self.provinces.get(build.province)
                if not prov or prov.owner != pid:
                    continue
                try:
                    btype = BuildingType(build.building_type)
                except ValueError:
                    continue
                bstats = BUILDING_STATS[btype]
                if player.age < bstats[1]:
                    continue
                if prov.has_building(btype):
                    continue  # no duplicates
                cost = bstats[0]
                if not player.can_afford(cost):
                    continue
                # Masonry: instant completion (already instant, but future-proof)
                player.pay(cost)
                prov.buildings.append(Building(type=btype, done=True))
                events.append(f"🏠 {pid} built {btype.value} at {prov.name}")

    # ── Research & Age Up ────────────────────────────────────────────────

    def process_research(self, all_orders: dict[str, Orders], events: list[str]):
        for pid, orders in all_orders.items():
            player = self.players[pid]
            if not player.alive or not orders.research:
                continue
            r = orders.research

            if r.tech == "age_up":
                next_age = player.age + 1
                if next_age > 3:
                    continue
                cost = AGE_COST[next_age]
                cost = player.civ_tech_discount(cost)
                if not player.can_afford(cost):
                    continue
                player.pay(cost)
                player.age = next_age
                events.append(f"⬆️ {pid} advanced to Age {next_age} ({'Bronze' if next_age==1 else 'Iron' if next_age==2 else 'Steel'})")
            else:
                try:
                    tech = TechId(r.tech)
                except ValueError:
                    continue
                if not can_research(player.age, player.techs, tech):
                    continue
                cost = TECH_COST[tech]
                cost = player.civ_tech_discount(cost)
                if not player.can_afford(cost):
                    continue
                player.pay(cost)
                player.techs.append(tech)
                events.append(f"🔬 {pid} researched {tech.value}")

    # ── Trade Routes ─────────────────────────────────────────────────────

    def process_trade_routes(self, all_orders: dict[str, Orders], events: list[str]):
        for pid, orders in all_orders.items():
            player = self.players[pid]
            if not player.alive:
                continue
            for tr_order in orders.trade_routes:
                fp = self.provinces.get(tr_order.from_province)
                tp = self.provinces.get(tr_order.to_province)
                if not fp or not tp:
                    continue
                if fp.owner != pid:
                    continue
                if not fp.has_building(BuildingType.TRADE_POST):
                    continue
                if not tp.has_building(BuildingType.TRADE_POST):
                    continue
                # Check no duplicate route
                exists = any(r.from_province == fp.id and r.to_province == tp.id
                             for r in self.trade_routes)
                if exists:
                    continue
                route = TradeRoute(
                    id=f"tr_{fp.id}_{tp.id}",
                    from_province=fp.id, to_province=tp.id,
                    owner=pid,
                    partner=tp.owner if tp.owner != pid else None,
                )
                self.trade_routes.append(route)
                events.append(f"📦 {pid} established trade route: {fp.name} → {tp.name}")

    # ── Verdanti Herbalist Healing ───────────────────────────────────────

    def process_healing(self, events: list[str]):
        """Verdanti herbalist: heal 1 veteran point to a unit in same province."""
        # This is simplified — just mark it as a civ perk for future expansion
        pass

    # ── Victory & Elimination ────────────────────────────────────────────

    def check_eliminations(self) -> list[str]:
        eliminated = []
        for pid, player in self.players.items():
            if not player.alive:
                continue
            if not self.player_provinces(pid) and not self.player_units(pid):
                player.alive = False
                eliminated.append(pid)
        return eliminated

    def check_victory(self) -> str | None:
        alive = [p for p in self.players.values() if p.alive]
        if len(alive) == 1:
            return alive[0].id

        # Domination: 15+ of 24 provinces
        for p in alive:
            if len(self.player_provinces(p.id)) >= 15:
                return p.id

        # Economic: 100 gold
        for p in alive:
            if p.gold >= 100 and any(pr.owner == p.id for pr in self.provinces.values()):
                return p.id

        # Score at max turns
        if self.turn >= self.max_turns:
            for p in alive:
                provs = len(self.player_provinces(p.id))
                units = len(self.player_units(p.id))
                p.score = provs * 3 + units + p.gold // 5 + len(p.techs) * 5 + p.age * 10
            return max(alive, key=lambda p: p.score).id

        return None

    # ── Diplomacy ─────────────────────────────────────────────────────────

    def process_diplomacy(self, all_orders: dict[str, Orders], events: list[str]):
        for pid, orders in all_orders.items():
            if not orders.diplomacy:
                continue
            d = orders.diplomacy

            # Messages
            for msg in d.messages:
                to = msg.get("to", "public")
                content = msg.get("content", "")
                is_public = (to == "public")
                self.messages.append(DiplomacyMessage(
                    sender=pid, recipient=to, content=content,
                    turn=self.turn, is_public=is_public,
                ))
                if is_public:
                    events.append(f"💬 {pid} (public): {content[:60]}")

            # Treaty proposals
            for prop in d.proposals:
                target = prop.get("target")
                ttype = prop.get("type", "alliance")
                if target not in self.players or target == pid:
                    continue
                self._treaty_uid += 1
                tp = TreatyProposal(
                    id=f"tp_{self._treaty_uid}",
                    proposer=pid, target=target,
                    treaty_type=TreatyType(ttype),
                    turn_proposed=self.turn,
                )
                self.proposals.append(tp)
                events.append(f"📜 {pid} proposed {ttype} to {target}")

            # Accept proposals
            for tp_id in d.accept_treaties:
                for tp in self.proposals:
                    if tp.id == tp_id and tp.target == pid and not tp.accepted and not tp.rejected:
                        tp.accepted = True
                        self._treaty_uid += 1
                        treaty = Treaty(
                            id=f"t_{self._treaty_uid}",
                            type=tp.treaty_type,
                            parties=[tp.proposer, tp.target],
                            turn_created=self.turn,
                        )
                        self.treaties.append(treaty)
                        events.append(f"🤝 {tp.proposer} & {pid}: {tp.treaty_type.value} formed!")

            # Reject proposals
            for tp_id in d.reject_treaties:
                for tp in self.proposals:
                    if tp.id == tp_id and tp.target == pid:
                        tp.rejected = True

            # Break treaties
            for t_id in d.break_treaties:
                for t in self.treaties:
                    if t.id == t_id and pid in t.parties and t.active:
                        t.broken_by = pid
                        t.turn_broken = self.turn
                        self.trust_penalties[pid] = self.trust_penalties.get(pid, 0) + 1
                        events.append(f"💔 {pid} broke {t.type.value} with {[p for p in t.parties if p != pid][0]}!")

    def get_diplomacy_for_player(self, pid: str) -> dict:
        """Get diplomacy info visible to a player."""
        msgs = [m for m in self.messages
                if m.turn == self.turn and (m.is_public or m.recipient == pid or m.sender == pid)]
        pending = [p for p in self.proposals if p.target == pid and not p.accepted and not p.rejected]
        active_treaties = [t for t in self.treaties if pid in t.parties and t.active]
        return {
            "messages": [{"from": m.sender, "to": m.recipient, "content": m.content,
                          "public": m.is_public} for m in msgs],
            "pending_proposals": [{"id": p.id, "from": p.proposer, "type": p.treaty_type.value}
                                  for p in pending],
            "treaties": [{"id": t.id, "type": t.type.value, "with": [p for p in t.parties if p != pid][0],
                          "since": t.turn_created} for t in active_treaties],
            "trust": {pid2: self.trust_penalties.get(pid2, 0) for pid2 in self.players},
        }

    def get_all_diplomacy(self, up_to_turn: int | None = None, public_only: bool = False) -> list[dict]:
        """Get all messages for spectator/replay."""
        msgs = self.messages
        if up_to_turn is not None:
            msgs = [m for m in msgs if m.turn <= up_to_turn]
        if public_only:
            msgs = [m for m in msgs if m.is_public]
        return [{"from": m.sender, "to": m.recipient, "content": m.content,
                 "turn": m.turn, "public": m.is_public} for m in msgs]

    # ── Unit list for agents ─────────────────────────────────────────────

    def get_player_units_list(self, pid: str) -> list[dict]:
        """Get detailed unit list with IDs for a player."""
        units = []
        for prov in self.provinces.values():
            for u in prov.units:
                if u.owner == pid:
                    units.append({
                        "id": u.id, "type": u.type.value,
                        "province": prov.id, "strength": u.strength,
                        "veteran": u.veteran,
                    })
        return units

    # ── Turn Processing ──────────────────────────────────────────────────

    def process_turn(self, all_orders: dict[str, Orders]) -> TurnResult:
        self.turn += 1
        events: list[str] = []
        result = TurnResult(turn=self.turn)

        # 0. Diplomacy
        self.process_diplomacy(all_orders, events)

        # 1. Research & age up (before builds so new age unlocks apply)
        self.process_research(all_orders, events)

        # 2. Moves & combat
        result.combats = self.process_moves(all_orders, events)

        # 3. Builds
        self.process_builds(all_orders, events)

        # 4. Trade routes
        self.process_trade_routes(all_orders, events)

        # 5. Collect resources
        result.income = self.collect_resources()

        # 6. Eliminations
        result.eliminations = self.check_eliminations()
        for e in result.eliminations:
            events.append(f"💀 {e} eliminated!")

        # 7. Victory
        result.winner = self.check_victory()
        if result.winner:
            self.winner = result.winner
            events.append(f"🏆 {result.winner} wins!")

        result.events = events
        self.history.append(result)
        return result

    # ── State Views ──────────────────────────────────────────────────────

    def get_player_view(self, pid: str) -> dict:
        """Compact player view for AI agents (~800-1200 tokens)."""
        player = self.players[pid]
        owned_ids = {p.id for p in self.player_provinces(pid)}

        # Visible = owned + adjacent + watchtower range
        visible = set(owned_ids)
        for p in self.player_provinces(pid):
            visible.update(p.adjacent)
            if p.has_building(BuildingType.WATCHTOWER):
                for adj_id in p.adjacent:
                    adj = self.provinces[adj_id]
                    visible.update(adj.adjacent)

        pv = {}
        for prov_id in visible:
            prov = self.provinces[prov_id]
            short_owner = prov.owner if prov.owner else "-"
            entry: dict = {
                "tr": TERRAIN_SHORT[prov.terrain],
                "o": short_owner,
                "adj": prov.adjacent,
            }
            if prov_id in owned_ids:
                # Full info for owned
                entry["u"] = prov.unit_counts()
                entry["b"] = [BUILDING_SHORT[b.type] for b in prov.buildings if b.done]
                entry["pr"] = list(prov.production(player.techs))
            else:
                # Partial: just owner and terrain, maybe unit count if adjacent
                total_units = len(prov.units)
                if total_units > 0:
                    entry["uc"] = total_units  # just count, no breakdown
            pv[prov_id] = entry

        fog = [pid2 for pid2 in self.provinces if pid2 not in visible]

        # Trade routes involving this player
        routes = []
        for tr in self.trade_routes:
            if tr.owner == pid or tr.partner == pid:
                routes.append([tr.from_province, tr.to_province, tr.income])

        return {
            "t": self.turn,
            "p": pid,
            "c": player.civ,
            "a": player.age,
            "r": player.resources,
            "tc": [t.value for t in player.techs],
            "pv": pv,
            "fog": fog,
            "tr": routes,
            "units": self.get_player_units_list(pid),
            "diplo": self.get_diplomacy_for_player(pid),
        }

    def get_full_state(self) -> dict:
        """Full state for spectators — includes everything."""
        provinces = {}
        for pid, prov in self.provinces.items():
            units_by_owner: dict[str, list[int]] = {}
            for u in prov.units:
                if u.owner not in units_by_owner:
                    units_by_owner[u.owner] = [0] * len(UNIT_ORDER)
                idx = UNIT_ORDER.index(u.type) if u.type in UNIT_ORDER else 0
                units_by_owner[u.owner][idx] += 1

            # Calculate production for this province
            prod = None
            if prov.owner and prov.owner in self.players:
                owner_player = self.players[prov.owner]
                f, i, g = prov.production(owner_player.techs)
                if owner_player.civ == "verdanti":
                    f += 1
                for u in prov.units:
                    if u.owner == prov.owner:
                        if u.type == UnitType.SAGE:
                            f += 1; i += 1; g += 1
                        elif u.type == UnitType.HERBALIST:
                            f += 2
                prod = [f, i, g]

            provinces[pid] = {
                "name": prov.name,
                "terrain": TERRAIN_SHORT[prov.terrain],
                "owner": prov.owner,
                "x": prov.x, "y": prov.y,
                "units": units_by_owner,
                "unit_count": len(prov.units),
                "strength": sum(u.strength for u in prov.units),
                "buildings": [BUILDING_SHORT[b.type] for b in prov.buildings if b.done],
                "adjacent": prov.adjacent,
                "defense": prov.defense_bonus,
                "income": prod,
            }

        players = {}
        for pid, p in self.players.items():
            # Calculate total income for this player
            inc = [0, 0, 0]
            if p.alive:
                for prov in self.player_provinces(pid):
                    pi = provinces.get(prov.id, {}).get("income")
                    if pi:
                        inc[0] += pi[0]; inc[1] += pi[1]; inc[2] += pi[2]
                # Upkeep
                upkeep = sum(1 for u in self.player_units(pid)
                             if u.type not in (UnitType.MILITIA, UnitType.SCOUT))
                inc[0] -= upkeep
                inc[2] += self._calc_trade_income(pid)

            players[pid] = {
                "civ": p.civ,
                "age": p.age,
                "resources": p.resources,
                "income": inc,
                "techs": [t.value for t in p.techs],
                "alive": p.alive,
                "provinces": len(self.player_provinces(pid)),
                "units": len(self.player_units(pid)),
                "score": p.score,
            }

        routes = []
        for tr in self.trade_routes:
            routes.append({
                "from": tr.from_province, "to": tr.to_province,
                "owner": tr.owner, "partner": tr.partner, "income": tr.income,
            })

        active_treaties = [{"id": t.id, "type": t.type.value, "parties": t.parties,
                            "since": t.turn_created, "broken_by": t.broken_by}
                           for t in self.treaties]

        return {
            "turn": self.turn,
            "players": players,
            "provinces": provinces,
            "trade_routes": routes,
            "treaties": active_treaties,
            "trust": dict(self.trust_penalties),
            "winner": self.winner,
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    def _find_unit(self, uid: str) -> Unit | None:
        for prov in self.provinces.values():
            for u in prov.units:
                if u.id == uid:
                    return u
        return None
