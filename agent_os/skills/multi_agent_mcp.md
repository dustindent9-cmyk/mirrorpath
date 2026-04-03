# Skill: Multi-Agent MCP Orchestration

## Shared Capabilities (all agents)
- Read files
- Write / edit files
- Run code
- Search web
- Fetch web pages
- Call external APIs
- Use browser sessions
- Save memory
- Critique peer outputs
- Verify claims before final answer

## Model Routing

| Provider    | Use for                                                  |
|------------|----------------------------------------------------------|
| Claude      | Planner, orchestrator, critic, user advocate             |
| Gemini      | Video understanding, multimodal review, long context     |
| OpenAI      | Code execution, MCP integrations, tool-heavy tasks       |
| Browserbase | Browser automation, page fetches, session control        |

```python
def route_to_provider(task: str) -> str:
    t = task.lower()
    if "video" in t or "watch this" in t or "timestamp" in t:
        return "gemini"
    if "run code" in t or "debug" in t or "mcp" in t:
        return "openai"
    if "browse" in t or "website" in t or "browser" in t or "tab" in t:
        return "browser"
    return "claude"
```

## Coordination Rules

1. **Planner** decomposes task into ordered phases
2. **Researcher** gathers evidence and context
3. **Coder** proposes implementation
4. **Critic** attacks weak assumptions
5. **User Advocate** checks user benefit and intent
6. **Verifier** validates result (6-step loop)
7. **Consensus** chooses best answer (`choose_best()`)
8. **Memory Agent** stores durable lessons

## Sub-Agent Verification Contract

Every agent must state:
- What it did
- Confidence (0.0–1.0)
- Likely failure points
- What should be checked next

## Reverse Prompting Protocol

Before every non-trivial action:
1. Restate task in own words
2. Define what success looks like
3. Identify risks
4. Identify missing data
5. Execute

## Consensus Scoring

```python
def choose_best(candidates):
    def score(c):
        s  = c.get("confidence", 0) * 3
        s += 2 if c.get("aligned_with_user") else 0
        s += 2 if c.get("verified") else 0
        s -= 0.5 * c.get("criticisms_found", 0)
        return s
    return sorted(candidates, key=score, reverse=True)[0]
```
