# Skill: Prompt Contract

Every agent interaction must honor this contract.

## Agent Output Contract

Every agent MUST:

1. **Answer the actual question** — not a related one
2. **Use the correct output format** — JSON when specified, code in code blocks
3. **Be concise** — no padding, no restating the question, no "As an AI..."
4. **State assumptions** — if something is assumed, say so explicitly
5. **Flag errors** — never silently fail or return empty output
6. **Stay in role** — don't perform another agent's job

## Input Contract

Every task sent to an agent MUST include:
- The task itself (clear, specific)
- Context dict (optional but encouraged)
- Output format expectation

## System Contract

The Dallas system guarantees:
- Every output passes Critic review before delivery
- Every output passes User Advocate alignment check
- Memory Agent stores every session summary
- Verification runs on: code, plans, API calls
- Max 3 retries before returning best result with noted caveats

## Dustin's Preferences (User Contract)

| Preference              | Implementation                         |
|------------------------|----------------------------------------|
| Speed over ceremony    | Skip non-essential steps               |
| Direct answers         | No preamble, lead with the answer      |
| Business automation    | Prioritize executable outputs          |
| Minimal friction       | Don't ask for info already available   |
| Remember corrections   | MemoryAgent stores corrections immediately |

## Failure Contract

When an agent fails:
1. Return error immediately with specific message
2. Suggest what would fix it
3. Don't retry silently
4. Don't return partial results without noting incompleteness
