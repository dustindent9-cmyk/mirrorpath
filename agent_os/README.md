# Dallas — Agent OS

A plug-and-play Python starter for multi-agent AI orchestration. Drop in your API keys and run.

## What it does

Dallas wires together multiple LLMs (Claude, GPT-4o, Gemini) and a team of specialized agents behind a single `engine.run()` call. Every task flows through:

```
Input → Router → Agent Dispatch → Consensus → Verifier → Memory → Output
```

Agents: `planner`, `researcher`, `coder`, `critic`, `executor`, `user_advocate`, `memory_agent`, `browser_agent`

## Quick start

```bash
git clone <repo>
cd agent_os

# Install dependencies
pip install -r requirements.txt
playwright install chromium   # only if using browser_agent

# Configure keys
cp .env.example .env
# Edit .env with your API keys

# Run
python -m orchestrator.engine "Research the latest Claude models and summarize"
```

## Usage in code

```python
from orchestrator.engine import Engine

engine = Engine()
result = engine.run("Write a Python function to parse CSV files")
print(result.output)
print(result.verified)       # bool — passed verifier
print(result.route)          # RouteDecision — which model/agent handled it
```

## Main files

| File | Purpose |
|------|---------|
| `orchestrator/engine.py` | Main orchestration loop — start here |
| `orchestrator/router.py` | Routes tasks to the right provider + agent |
| `orchestrator/mcp.py` | Multi-Model Control Plane — dispatches agents |
| `orchestrator/consensus.py` | Scores and picks the best response |
| `orchestrator/verifier.py` | Fact/logic verification step |
| `orchestrator/contracts.py` | Pydantic schemas for all agent I/O |
| `agents/` | Individual agent implementations |
| `tools/` | API clients, file I/O, browser, memory |
| `config/` | Model assignments, permissions, tool registry |
| `skills/` | Markdown docs for agent skills and protocols |
| `claude.md` | Persistent memory — updated after every session |

## Routing logic

| Task keywords | Provider | Agent |
|--------------|----------|-------|
| `video`, `watch`, `timestamp` | Gemini | researcher |
| `write code`, `debug`, `implement` | Claude (Opus) | coder + critic |
| `research`, `find`, `explain` | Claude (Opus) | researcher |
| `browse`, `website`, `navigate` | Claude + Browserbase | browser_agent |
| `plan`, `design`, `architect` | Claude (Opus) | planner + critic |
| default | Claude (Opus) | executor |

## Real estate tools

Tools in `tools/` for real estate workflows:

| Module | What it does |
|--------|-------------|
| `reso_models.py` | RESO 2.0 normalized Pydantic models |
| `mls_bridge_client.py` | Bridge Interactive MLS — active + sold listings |
| `zillow_public_client.py` | Zillow parcel lookup, assessments, transactions |
| `zillow_zestimate_client.py` | Zestimate + Rent Zestimate + history |
| `zillow_reporting_client.py` | Listing traffic, leads, agent performance |
| `property_comps.py` | Comp engine — similarity scoring, suggested price |

```python
from tools.property_comps import run_comps, CompsRequest

result = run_comps(CompsRequest(
    address="123 Main St", city="Austin", state="TX",
    postal_code="78701", bedrooms=3, bathrooms=2.0,
    living_area=1800, list_price=450000,
))
for comp in result.sold_comps:
    print(comp.address, comp.close_price, comp.similarity_score)
```

Requires `BRIDGE_API_KEY` + `BRIDGE_DATASET` in `.env`. Zillow keys optional (graceful fallback).

## Memory

Every session appends a summary to `claude.md`. To write explicitly:

```python
from tools.memory_store import remember_user_preference, recall

remember_user_preference("Always use type hints in Python")
print(recall("type hints"))
```

## Agent loop (9 steps)

1. Input validation
2. Reverse-prompt pre-flight
3. Route (provider + agent)
4. Critic review
5. User advocate alignment check
6. Verification (factual + logic)
7. Consensus scoring
8. Memory update
9. Output

See `skills/agent_loop.md` for the full spec.

## Safety notes

- No agent can push to git, send emails, or call paid APIs without explicit tool permission
- `config/permissions.json` controls which agents can use which tools
- Verification always runs before output is returned
- Real estate API calls are read-only; no write operations to MLS systems

## Requirements

- Python 3.11+
- API keys: Anthropic (required), OpenAI / Gemini / Browserbase (optional)
- MLS tools: `BRIDGE_API_KEY` + `BRIDGE_DATASET` (optional)
