# Skill: Agent Loop

The core execution cycle for Dallas multi-agent system.

## Loop Sequence

1. **Receive user input**
   - Capture raw task/question from user
   - Load relevant memories from MemoryAgent

2. **Planner breaks task into steps**
   - Planner agent decomposes into ordered phases
   - Each phase assigned to a specific agent role
   - Dependencies identified

3. **Assign to agents**
   - Researcher → gather info, find facts, context
   - Coder → build solution, write/fix code
   - Executor → run tasks, call APIs, manage files

4. **Critic reviews output**
   - Scores on: correctness, completeness, quality, safety, alignment
   - Returns issues + recommendations
   - If score < 0.7 → revise loop

5. **User Advocate checks alignment**
   - Verifies output matches original user intent
   - Flags scope creep or missed requirements
   - Dustin context: automation, speed, minimal friction

6. **Verifier validates correctness**
   - Factual check
   - Logic consistency
   - Tool output validation
   - Code execution if applicable
   - Approves or sends back for revision

7. **Consensus system resolves disagreements**
   - Scores all agent responses
   - Picks best by: confidence, no errors, user alignment
   - Arbitrates with meta-Claude call if divergent

8. **Memory Agent stores learnings**
   - Session summary stored
   - Key facts and outcomes persisted
   - User preferences updated

9. **Return final answer**

## Exit Conditions
- All verifications pass
- Max retries (3) exhausted → return best result with caveats
- User explicitly cancels

## Retry Logic
- Critic score < 0.7 → revise with specific feedback
- Verifier fails → return to responsible agent
- Consensus diverges → arbitrate once, then accept best
