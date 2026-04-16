// Dallas Copilot — Background Service Worker (MV3)

// Forward the "new-chat" command to the popup (if open)
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "new-chat") {
    // Try to message an existing popup
    const views = chrome.extension.getViews({ type: "popup" });
    if (views.length > 0) {
      chrome.runtime.sendMessage({ type: "new-chat" });
    } else {
      // Popup isn't open — open it; user will land on a fresh session by default
      chrome.action.openPopup().catch(() => {});
    }
  }
});

// On install: set default storage values
chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === "install") {
    chrome.storage.sync.set({
      dallasBases: "http://localhost:8000",
      dallas_sessions: [],
    });
  }
});
