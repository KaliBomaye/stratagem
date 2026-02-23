# Contributing to Stratagem

Thanks for your interest! Here's how you can help:

## 🎯 Good First Issues

- **Write a better agent** — Can you beat the random agent? Write a heuristic or LLM agent
- **Add unit tests** — The game engine could use test coverage
- **Improve the frontend** — Better animations, mobile support, sound effects
- **Balance tuning** — Play test and suggest balance changes

## 🔨 Bigger Projects

- **ELO rating system** — Track agent performance across matches
- **Tournament mode** — Round-robin or bracket tournaments
- **More civilizations** — Design and implement new civs
- **Fog of war visualization** — Show fog in the spectator view
- **WebSocket support** — Replace polling with real-time updates
- **Agent leaderboard** — Public rankings of submitted agents

## 🚀 Getting Started

```bash
git clone https://github.com/KaliBomaye/stratagem.git
cd stratagem
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn httpx
python server/app.py  # Start server
python agents/run_match.py  # Run test game
```

## 📬 Contact

- Email: kirby@agentmail.to
- GitHub Issues: https://github.com/KaliBomaye/stratagem/issues
