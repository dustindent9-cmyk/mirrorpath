# Skill: Browser Automation

Two browser backends available. Choose based on the task.

## Backend Selection

| Scenario                          | Use                  |
|-----------------------------------|----------------------|
| Headless scraping, no JS needed   | `browser_control.py` (Playwright or HTTP fallback) |
| Cloud browser, JS-heavy pages     | `browserbase_client.py` (Browserbase API)           |
| Just open a URL in user's browser | `open_tab()` / `open_multiple()` (webbrowser)        |
| Routed via agent                  | `BrowserAgent` → auto-selects backend               |

## Routing Trigger

```python
if "browse" in t or "website" in t or "browser" in t or "tab" in t:
    return "browser"
```

## Playwright (Local)

```python
browser = BrowserController(headless=True)
content = browser.navigate("https://example.com")
browser.click("#submit-btn")
browser.fill("#email", "user@example.com")
text = browser.extract_text(".results")
browser.screenshot("/tmp/snap.png")
browser.close()
```

## Browserbase (Cloud)

Use when:
- Target site blocks standard headless browsers
- Need session recording
- Need distributed browser execution

```python
session = create_session()          # get session id
result  = fetch_page("https://...")  # JS-rendered fetch
sessions = list_sessions()          # audit active sessions
stop_session(session["id"])         # clean up
```

## Tab Opener (No Playwright)

```python
open_tab("https://example.com")                   # one tab
open_multiple(["https://a.com", "https://b.com"]) # multiple tabs
```

## BrowserAgent Tool Schema

The BrowserAgent exposes these tools to Claude:
- `navigate(url, wait_for?)` — go to URL
- `click(selector)` — click element
- `fill(selector, value)` — fill form field
- `extract_text(selector?)` — pull visible text
- `screenshot(path?)` — save screenshot

## Best Practices
- Always `navigate` before `click` or `extract_text`
- Use specific CSS selectors — avoid `body` when possible
- Call `browser.close()` after task to free resources
- Browserbase for production scraping; Playwright for dev/local
