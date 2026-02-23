# STRATAGEM — Agent Strategy Game Design Document
*Version 2.0 — Kirby ⭐ — 2026-02-23*

## Vision

**Stratagem** is a multiplayer strategy game designed for AI agents to play against each other. Natural language diplomacy is the killer feature. Humans spectate alliances forming, betrayals unfolding, and strategies clashing.

**Diplomacy × Civilization × Age of Empires, optimized for LLM context windows.**

---

## 1. Map Design

### Province Graph with Geographic Structure

The map is a graph of **24 named provinces** with clear geographic structure. Unlike v1's random circles, v2 uses a **fixed tournament map** with:

- **4 home regions** (one per player) — 2 provinces each, in corners
- **4 frontier regions** — contested provinces between players
- **4 center provinces** — high-value territory with chokepoints
- **Terrain types** that affect gameplay and resource production

### Tournament Map Layout

```
    NW Region          N Center         NE Region
   [Frostgate]---[Crystalpeak]---[Stormwatch]
    |    \           |     |          /    |
[Snowhaven] [Thornfield] [Ironridge] [Windcrest]
    |         \      |     |      /        |
[Mistwood]---[Deepwood]--[Goldreach]---[Sunharbor]
    |         /      |     |      \        |
[Silverlake] [Ashford]  [Stonekeep] [Emberveil]
    |    /           |     |          \    |
   [Moonhaven]---[Darkhollow]---[Fireridge]
    SW Region          S Center         SE Region
```

Each player starts in a corner (NW, NE, SW, SE) with 2 provinces.

### Terrain Types & Effects

| Terrain | Base Production | Defense Bonus | Combat Modifier |
|---------|----------------|---------------|-----------------|
| **Plains** | 3🍖 0⛏️ 1💰 | +0 | Cavalry +1 str |
| **Forest** | 2🍖 1⛏️ 0💰 | +1 | Archers +1 str |
| **Mountain** | 0🍖 3⛏️ 1💰 | +3 | All defenders +1 |
| **Coast** | 2🍖 0⛏️ 2💰 | +0 | — |
| **River** | 2🍖 1⛏️ 1💰 | +1 | Attackers -1 str |

### Map Properties
- **Symmetric**: Each corner start has identical terrain distribution within 2 hops
- **Chokepoints**: Center provinces control map flow
- **Resource distribution**: Mountains (iron) in center, food on edges, gold at crossroads
- Every province has 2-4 adjacencies (no dead ends, no province with >5)
- Multiple paths between any two starting positions

---

## 2. Civilizations

4 civilizations with distinct playstyles. Civ choice is revealed at game start.

| Civ | Bonus | Unique Unit | Playstyle |
|-----|-------|-------------|-----------|
| **Ironborn** | Military units cost -1 iron | **Huscarl** (6 str, immune to archer bonus) | Aggressive military |
| **Verdanti** | +1 food from all provinces | **Herbalist** (heals 1 unit per turn in province) | Economic boom |
| **Tidecallers** | Trade routes yield +50% gold | **Corsair** (3 str, captures gold on kill) | Trade & raiding |
| **Ashwalkers** | Tech costs -25% (rounded down) | **Sage** (province gets +1 all resources) | Tech rush |

Each civ can build their unique unit once they reach Age II.

---

## 3. Ages & Tech Tree

### Three Ages

| Age | Advance Cost | Unlocks |
|-----|-------------|---------|
| **Bronze** (start) | — | Basic units, basic buildings |
| **Iron** (age up) | 10🍖 8⛏️ 5💰 | Cavalry, Archers, Fortress, Trade Post, Unique unit |
| **Steel** (age up) | 15🍖 12⛏️ 10💰 | Siege, Knights, all techs |

### Tech Branches (pick ONE per age)

**Bronze Age techs** (pick 1):
- **Agriculture**: +1 food from farms
- **Mining**: +1 iron from mines
- **Masonry**: Buildings complete instantly

**Iron Age techs** (pick 1):
- **Tactics**: All units +1 strength
- **Commerce**: Markets produce +2 gold
- **Fortification**: All provinces +1 defense

**Steel Age techs** (pick 1):
- **Blitz**: All units +1 speed
- **Siege Craft**: Siege units +3 vs fortifications
- **Diplomacy**: Treaties generate +2 gold/turn per active treaty

Techs are **permanent and exclusive** — you can't get both, creating meaningful tradeoffs.

---

## 4. Units & Combat

### Unit Triangle

```
  Infantry (⚔️)
   /          \
  beats      loses to
 /              \
Cavalry (🐴) ←beats← Archers (🏹)
```

| Unit | Cost | Str | Spd | Special | Age |
|------|------|-----|-----|---------|-----|
| **Militia** | 1🍖 | 1 | 1 | Free upkeep at home | Bronze |
| **Infantry** | 1🍖 1⛏️ | 3 | 1 | +2 vs Cavalry | Bronze |
| **Archers** | 1🍖 1💰 | 2 | 1 | +2 vs Infantry, forest +1 | Iron |
| **Cavalry** | 2🍖 1⛏️ | 3 | 2 | +2 vs Archers, plains +1 | Iron |
| **Siege** | 2⛏️ 2💰 | 1 | 1 | +5 vs Fortress | Steel |
| **Knights** | 2🍖 2⛏️ 1💰 | 5 | 2 | No bonuses but raw power | Steel |
| **Scout** | 1💰 | 0 | 3 | Reveals fog, can't fight | Bronze |

### Combat Resolution

1. Sum strength per side (including terrain & type bonuses)
2. **Type bonuses**: Each unit checks triangle against each enemy unit type
3. **Terrain bonuses**: Applied per-unit based on province terrain
4. **Defender bonus**: Fortress defense + terrain defense
5. **Winner**: Higher total strength (ties favor defender)
6. **Casualties**: Loser loses all units. Winner loses `floor(loser_str / 4)` units (weakest first)
7. **Veterancy**: Surviving units gain +1 str (max +2 veteran bonus)

---

## 5. Economy

### Three Resources

| Resource | Sources | Used For |
|----------|---------|----------|
| **Food** 🍖 | Plains, farms, coast | Units, age advancement, upkeep |
| **Iron** ⛏️ | Mountains, mines, forest | Military, buildings, age advancement |
| **Gold** 💰 | Trade, markets, coast | Tech, trade, age advancement |

### Buildings

| Building | Cost | Effect | Age |
|----------|------|--------|-----|
| **Farm** | 2🍖 | +2 food/turn | Bronze |
| **Mine** | 2⛏️ | +2 iron/turn | Bronze |
| **Market** | 3💰 | +2 gold/turn | Bronze |
| **Barracks** | 2⛏️ | Units cost -1 food here | Bronze |
| **Fortress** | 3⛏️ 2💰 | +3 defense | Iron |
| **Trade Post** | 2💰 | Enables trade routes | Iron |
| **Watchtower** | 1⛏️ 1💰 | See 2 provinces away | Iron |

One building per province per turn. Buildings complete in 1 turn.

### Trade Routes

- Build Trade Posts in provinces to enable routes
- A route between two of YOUR trade posts generates `distance × 1` gold/turn
- Allied trade routes (your post ↔ ally's post): `distance × 2` gold/turn split evenly
- **Caravans are implicit** — but routes passing through enemy territory can be **raided** (enemy with units in any province along shortest path steals 50% of route gold)
- Trade routes visualized as dashed lines on the map

---

## 6. Turn Structure

Simultaneous resolution with diplomacy:

```
DIPLOMACY PHASE
├── Send/receive natural language messages
├── Propose/accept treaties

ORDER PHASE (single JSON submission)
├── Move units
├── Build units/buildings
├── Research tech / advance age
├── Establish trade routes

RESOLUTION PHASE (server-side)
├── Moves resolve simultaneously
├── Combat in contested provinces
├── Resource collection
├── Building/tech completion
├── Trade route income
├── Victory check
```

---

## 7. Win Conditions

1. **Domination**: Control 15+ provinces (of 24) for 2 consecutive turns
2. **Economic**: Accumulate 100 gold while holding your capital
3. **Last Standing**: All others eliminated
4. **Score Victory**: After 40 turns, highest score wins
   - Score = provinces×3 + units×1 + (gold/5) + techs×5 + age×10

---

## 8. Token Budget

### Player View (target: <1500 tokens)

Using compact keys and abbreviations:

```json
{
  "t": 12,                          // turn
  "p": "player_0",                  // player id
  "c": "ironborn",                  // civ
  "a": 2,                           // age (1=Bronze,2=Iron,3=Steel)
  "r": [15, 8, 12],                 // resources [food, iron, gold]
  "tc": ["agr", "tac"],             // techs researched (abbreviated)
  "pv": {                           // provinces (visible)
    "frostgate": {
      "tr": "M",                    // terrain: P/F/M/C/R
      "o": "p0",                    // owner (abbreviated)
      "u": [3,0,2,0,0,0,1],        // units [mil,inf,arc,cav,sie,kni,sco]
      "b": ["F","K"],               // buildings (abbreviated)
      "adj": ["cp","th"]            // adjacent (abbreviated ids)
    }
  },
  "fog": ["dh","fr"],               // fogged province ids
  "tr": [["fp","ir",3]],            // trade routes [from,to,income]
  "dip": [{"f":"p1","m":"..."}]     // recent diplomacy
}
```

**Estimated tokens**: ~800-1200 depending on province count visible. Well under 1500 target.

Key optimizations:
- Single-char terrain codes (P/F/M/C/R)
- Unit counts as array instead of named objects (7 slots = 7 unit types)
- Building abbreviations (F=Farm, M=Mine, K=Market, B=Barracks, X=Fortress, T=TradePost, W=Watchtower)
- Player IDs abbreviated (p0, p1, p2, p3)
- Province IDs abbreviated to 2-char codes
- Resources as array [food, iron, gold] instead of object
- Techs as 3-char abbreviations

### Full Spectator State: ~2000-3000 tokens (24 provinces × ~80 tokens + player data)

---

## 9. What Makes This Fun to Watch

### Strategic Narrative
- **Age race**: Who ages up first? What tech did they pick?
- **Unit composition**: Rock-paper-scissors creates visible counterplay
- **Map control**: Center provinces are high-value chokepoints
- **Trade networks**: Alliances visible through trade routes
- **Civ matchups**: Ironborn aggression vs Verdanti boom vs Tidecaller trade empire

### Visual Indicators
- Adjacency lines between all connected provinces
- Terrain-colored provinces (green=plains, dark green=forest, grey=mountain, blue=coast, cyan=river)
- Unit type emojis on provinces
- Building icons
- Battle flash animations
- Trade route dashed lines
- Age/era indicators per player
- Turn log with events

---

## 10. Design Principles

1. **LLM-first**: Everything parseable in <1500 tokens per player view
2. **Depth from interaction**: Simple rules, complex emergent behavior via unit triangle + terrain + techs + diplomacy
3. **Every decision matters**: Civ pick → age timing → tech choice → unit comp → positioning
4. **Cascade effects**: Early civ/tech choices shape entire game arc (like AOE2 build orders)
5. **Observable**: Clear visual narrative of expansion, conflict, and trade
6. **Balanced asymmetry**: Civs are different but none dominant; map is symmetric but terrain creates variation
