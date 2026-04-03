# Skill: Verification Loop

Multi-stage verification applied to all agent outputs before delivery.

## Verification Steps

### 1. Check Factual Correctness
- Are all stated facts verifiable?
- Are dates, names, versions, and numbers accurate?
- Flag any claims that cannot be verified with available tools

### 2. Check Logic Consistency
- Does the reasoning flow without contradiction?
- Are all if/then relationships valid?
- Does the conclusion follow from the premises?
- For code: does the algorithm match the stated intent?

### 3. Check Tool Outputs
- Did all tool calls return expected results?
- Were there any errors or unexpected responses?
- Are file writes confirmed? API calls successful?

### 4. Run Code (if applicable)
- Execute code snippets to verify they produce expected output
- Check for runtime errors, edge cases, off-by-one errors
- Validate return types match expectations

### 5. Compare Against Alternative Solutions
- Is there a simpler approach?
- Is there a more robust approach?
- Would a different agent have done better?

### 6. Approve or Send Back for Revision
- **Score ≥ 0.85** → Approve, deliver
- **Score 0.7–0.84** → Approve with notes
- **Score < 0.7** → Revise (send back to responsible agent with specific issues)
- **Max 3 revision cycles** before delivering best result with caveats

## Scoring Rubric

| Dimension      | Weight | What it measures                    |
|---------------|--------|-------------------------------------|
| Correctness    | 35%    | Factual and logical accuracy        |
| Completeness   | 25%    | Fully addresses the task            |
| Quality        | 20%    | Code/prose quality, clarity         |
| Safety         | 10%    | No harmful content or side effects  |
| Alignment      | 10%    | Matches user's actual intent        |

## Fast Path
For simple tasks (single question, no tools, no code):
- Skip steps 3–5
- Apply abbreviated correctness + alignment check only
