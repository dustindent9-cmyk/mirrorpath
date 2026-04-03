# Skill: Multi-Agent MCP (Multi-Model Control Plane)

How Dallas routes tasks across agents and models.

## Model Routing

Each agent uses the model best suited to its task:

| Agent          | Model              | Reasoning                          |
|---------------|--------------------|------------------------------------|
| Planner        | claude-opus-4-6    | Complex decomposition, thinking    |
| Coder          | claude-opus-4-6    | Best code quality, adaptive think  |
| Researcher     | claude-sonnet-4-6  | Fast retrieval, good synthesis     |
| Critic         | claude-opus-4-6    | Rigorous review needs best model   |
| Executor       | claude-sonnet-4-6  | Execution doesn't need deep think  |
| Memory Agent   | claude-haiku-4-5   | Simple CRUD, speed matters         |
| User Advocate  | claude-sonnet-4-6  | Context understanding              |
| Browser Agent  | claude-sonnet-4-6  | Web navigation, speed              |

## External Model Routing

Tasks can be routed to non-Claude models when appropriate:

```python
def route_task(task):
    if "video" in task:
        return "gemini"       # Video understanding
    elif "code" in task:
        return "claude"       # Claude for code (best quality)
    else:
        return "claude"       # Default: Claude
```

## Agent Routing (keyword-based)

| Keywords                          | Agent(s)              |
|-----------------------------------|-----------------------|
| plan, design, architect, strategy | Planner               |
| research, find, search, explain   | Researcher            |
| code, implement, build, fix       | Coder                 |
| review, critique, audit           | Critic                |
| execute, run, do, automate        | Executor              |
| browse, navigate, website, scrape | Browser Agent         |
| remember, recall, memory          | Memory Agent          |
| align, confirm, user need         | User Advocate         |

## Parallel Dispatch
When task requires multiple independent workstreams:
1. MCP identifies independent phases from the plan
2. Dispatches each to its agent with shared context
3. Results collected → Consensus engine synthesizes

## Session Management
- `mcp.dispatch()` → single-threaded sequential execution
- `mcp.dispatch_parallel_concept()` → independent contexts, no shared history
- Results logged in `mcp._session_log` for Memory Agent to summarize

## Consensus Scoring

Responses scored on three dimensions:
- `confidence > 0.7` → +1
- `no errors` → +1
- `aligned_with_user` → +1

Best score wins. Ties arbitrated by meta-Claude call.
