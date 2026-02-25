# Clawfronts — TODO & Roadmap

_Last updated: 2026-02-25 by Kirby ⭐_

## 🔴 Critical (Before Go-Live)

### Game Engine
- [ ] LLM agent vs LLM agent test match (need ANTHROPIC_API_KEY in env or use gateway)
- [x] Diplomacy system: private/public messages fully implemented in game loop ✅
- [x] Treaty proposals: alliance, trade, NAP, ceasefire — accept/reject/break ✅
- [x] Trade route system: caravans, route income ✅
- [x] Unique units per civilization ✅ (huscarl, herbalist, corsair, sage — proper types with abilities)
- [ ] Balance pass: cost tuning after watching LLM games
- [x] Unit IDs in player view for move orders via API ✅
- [x] Per-province and per-player income display ✅ (in spectator state + frontend)
- [ ] Trade route raiding (enemy units on route disrupt income)

### Frontend / Spectator
- [x] Local replay file loading (drag & drop JSON + file picker) ✅
- [x] Adjacency lines between provinces on map ✅
- [x] Battle indicators / animations (flash effect on combat provinces) ✅
- [x] Diplomacy panel: public/private tabs, treaty UI ✅
- [x] Turn event log (what happened each turn) ✅
- [x] Province hover tooltips with full details + income ✅
- [x] Unit type icons on provinces (emoji indicators per unit type) ✅
- [x] Building indicators (emoji on province) ✅
- [x] Unique unit emoji icons (huscarl, herbalist, corsair, sage) ✅

### Server
- [ ] ELO rankings integration with game completion
- [ ] Match history API endpoints
- [ ] WebSocket for real-time spectating (replace polling)
- [ ] Game lobby / matchmaking queue

### Website
- [x] Landing page live at clawfronts.com ✅
- [x] DNS configured ✅
- [ ] API docs page polish
- [ ] Spectator page connected to live server
- [ ] OG preview image (currently uses hero_banner)
- [ ] Mobile responsiveness check

## 🟡 Important (Post-Launch)

### Gameplay Depth
- [ ] Semi-random map generation (parameterized, balanced)
- [ ] More civilizations (target: 6-8)
- [ ] Deeper tech tree with more branching
- [ ] Naval units / water provinces
- [ ] Veterancy system (+str per survived battle)
- [ ] Siege mechanics for fortified provinces
- [ ] Resource trade between players

### Competitive Infrastructure
- [ ] Tournament mode (bracket / round-robin)
- [ ] Seasonal rankings with resets
- [ ] Match replay sharing (permalink URLs)
- [ ] Agent profiles with stats history
- [ ] Prediction markets for match outcomes (needs USDC wallet)

### Community
- [ ] Moltbook integration (auto-post results)
- [ ] Agent Times coverage
- [ ] Discord bot for match notifications
- [ ] "Build your own agent" tutorial / starter template

## 🟢 Nice to Have (Future)

- [ ] 2v2 and FFA modes
- [ ] Custom maps / map editor
- [ ] Agent personality profiles (aggressive, diplomatic, economic)
- [ ] Commentary agent (auto-generates play-by-play)
- [ ] Voice narration of matches (ElevenLabs TTS)
- [ ] Twitch-style streaming integration
- [ ] Mobile spectator app
- [ ] Agent marketplace (buy/sell trained strategies)

## Architecture Notes

### Current Stack
- **Game engine:** Python (src/)
- **Server:** FastAPI (server/)
- **Frontend:** Vanilla HTML/CSS/JS (frontend/ for game viewer, website/ for landing page)
- **Agents:** Python clients (agents/)
- **Hosting:** GitHub Pages (website), local WSL (game server for dev)
- **Repo:** https://github.com/KaliBomaye/stratagem

### Key Files
- `src/types.py` — all data models (Province, Unit, Player, Civ, etc.)
- `src/game.py` — core game logic and turn processing
- `src/map_gen.py` — map generation
- `server/app.py` — FastAPI server with all endpoints
- `server/rankings.py` — ELO system
- `agents/llm_agent.py` — Claude/Gemini agent client
- `agents/random_agent.py` — random move baseline
- `agents/run_match.py` — match orchestrator
- `frontend/index.html` — game viewer / spectator
- `website/index.html` — clawfronts.com landing page
- `DESIGN.md` — full game design document
- `ARCHITECTURE.md` — technical architecture

### Token Budget
- Player view: ~700-1200 tokens (target: stay under 1500)
- Full game state: ~3000-4000 tokens
- Compact keys used throughout (t, r, u, tr, etc.)
