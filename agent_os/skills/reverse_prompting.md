# Skill: Reverse Prompting

Technique applied **before** any agent executes a task.
Forces explicit prediction of the ideal outcome before attempting it.

## Protocol

Before executing any non-trivial task:

### 1. Restate the Task
Rephrase the task in your own words to confirm understanding.
If the restatement differs from the original → flag ambiguity first.

### 2. Predict a Perfect Answer
Describe what a perfect response would look like:
- Format (code / list / prose / JSON)
- Length (brief / detailed)
- What specific information it would contain
- What it would NOT contain

### 3. Identify Risks
List failure modes:
- What could go wrong technically
- What information might be missing or stale
- What assumptions might be wrong
- Side effects of actions

### 4. Identify Missing Info
What would you need to give a perfect answer that you don't have?
- Request it from user OR proceed with stated assumptions

### 5. Proceed
Now execute with the prediction as your target.

## Example

**Task:** "Write a Python function to retry HTTP requests"

**Restatement:** "Create a Python function that automatically retries failed HTTP requests with configurable backoff."

**Perfect Answer Looks Like:**
- Clean Python function, ~30 lines
- Parameters: url, max_retries, backoff_factor
- Uses `requests` or `httpx`
- Handles specific HTTP errors (429, 5xx)
- Has docstring and type hints

**Risks:**
- User might want async version
- Might need to preserve request body on retry
- Exponential vs linear backoff preference unknown

**Missing Info:**
- Sync or async? (assuming sync)
- Which HTTP library? (assuming httpx)

**→ Proceed with assumptions stated.**

## When to Apply
- Tasks with > 3 steps
- Any code generation
- Any API call with side effects
- Whenever the task is ambiguous
