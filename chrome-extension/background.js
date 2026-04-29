const MCP_URL = "http://127.0.0.1:8001/task";

// ── Create context menu on install AND on browser startup ─────────────────────
function registerContextMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "taskgenie-create",
      title: "⚡ Create Task with TaskGenie",
      contexts: ["selection"],
    });
    console.log("[TaskGenie] Context menu registered.");
  });
}

chrome.runtime.onInstalled.addListener(registerContextMenu);
chrome.runtime.onStartup.addListener(registerContextMenu);

// Also register immediately when service worker starts
registerContextMenu();


// ── Handle right-click menu click ─────────────────────────────────────────────
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "taskgenie-create") return;

  const selectedText = info.selectionText?.trim();
  if (!selectedText) return;

  console.log("[TaskGenie] Selected text:", selectedText);

  // Show "creating" feedback on the page
  await showAlert(tab.id, "🚀 Creating task with TaskGenie...");

  try {
    const response = await fetch(MCP_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_input: selectedText,
        context: {
          user_role: "developer",
          source: "chrome_extension",
          app: "TaskGenie",
        },
        available_tools: ["notion", "jira"],
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Server error: ${response.status}`);
    }

    const data = await response.json();
    console.log("[TaskGenie] Response:", data);

    const tool   = data.tool_used || "notion";
    const taskId = data.output?.task_id || "—";
    const prio   = data.output?.priority || "—";

    await showAlert(tab.id, `✅ Task created!\nTool: ${tool}\nPriority: ${prio}\nID: ${taskId}`);

  } catch (err) {
    console.error("[TaskGenie] Error:", err.message);
    await showAlert(tab.id, `❌ Failed to create task\n${err.message}`);
  }
});


// ── Inject an alert into the active tab ───────────────────────────────────────
function showAlert(tabId, message) {
  return chrome.scripting.executeScript({
    target: { tabId },
    func: (msg) => alert(msg),
    args: [message],
  });
}
