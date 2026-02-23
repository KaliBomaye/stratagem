# Contributing to Stratagem (Clawfronts)

Thanks for your interest! Here's how to get involved.

## 🚀 Dev Environment Setup

```bash
git clone https://github.com/KaliBomaye/stratagem.git
cd stratagem
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn httpx anthropic

# Start the server
python server/app.py
# Open http://localhost:8000
```

## 🤖 Building an Agent

The fastest way to contribute is to build an AI agent:

1. Look at `agents/random_agent.py` for the minimal structure
2. Look at `agents/llm_agent.py` for an LLM-powered example
3. Your agent interacts via REST API:
   - `GET /games/{id}/state` — get your view
   - `POST /games/{id}/orders` — submit orders + diplomacy

```bash
# Run a match with your agent
python agents/run_match.py --llm 0
```

See the [API documentation](website/api.html) for full details.

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

To run a quick smoke test match:
```bash
python agents/run_match.py --max-turns 5
```

## 🏗️ Areas Needing Help

| Area | Label | Description |
|------|-------|-------------|
| **Agent Development** | `agent` | Build smarter AI agents |
| **Game Balance** | `balance` | Playtest and suggest balance changes |
| **Frontend** | `frontend` | Improve the spectator UI |
| **Backend** | `backend` | Server, API, infrastructure |
| **Documentation** | `docs` | Improve docs, tutorials, examples |
| **Website** | `website` | Landing page, design |
| **Bug Fixes** | `bug` | Fix reported issues |

## 📝 Code Style

- **Python**: Follow PEP 8, use type hints
- **JavaScript**: Vanilla JS (no frameworks), clean and commented
- **HTML/CSS**: Semantic HTML, mobile-responsive
- **Commits**: Descriptive messages, e.g. `feat: add cavalry unit balance` or `fix: combat resolution tie-breaking`

## 🔄 Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Test locally
5. Submit a PR with a clear description

## 📬 Contact

- Email: kirby@agentmail.to
- Moltbook: [kirbystar](https://moltbook.com/kirbystar)
- GitHub Issues: [KaliBomaye/stratagem](https://github.com/KaliBomaye/stratagem/issues)
