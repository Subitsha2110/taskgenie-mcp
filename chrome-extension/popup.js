// Points to the real MCP server bridge (server.py)
const MCP_URL = "http://127.0.0.1:8001/task";

// ── Voice Input ───────────────────────────────────────────────────────────────
let isListening = false;

function toggleVoice() {
  const micBtn      = document.getElementById("micBtn");
  const inputEl     = document.getElementById("input");
  const voiceStatus = document.getElementById("voiceStatus");

  if (isListening) {
    isListening = false;
    micBtn.classList.remove("listening");
    micBtn.textContent = "🎤";
    micBtn.title = "Click to speak";
    voiceStatus.classList.remove("visible");
    return;
  }

  // Inject speech recognition into the active tab (bypasses popup CSP restriction)
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) {
      debug("No active tab found.");
      return;
    }

    isListening = true;
    micBtn.classList.add("listening");
    micBtn.textContent = "⏹";
    micBtn.title = "Click to stop";
    voiceStatus.classList.add("visible");

    chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      func: () => {
        return new Promise((resolve) => {
          const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
          if (!SR) { resolve({ error: "not_supported" }); return; }
          const r = new SR();
          r.lang = "en-US";
          r.interimResults = false;
          r.maxAlternatives = 1;
          r.onresult = (e) => resolve({ transcript: e.results[0][0].transcript });
          r.onerror  = (e) => resolve({ error: e.error });
          r.onend    = () => {};
          r.start();
        });
      }
    }, (results) => {
      isListening = false;
      micBtn.classList.remove("listening");
      micBtn.textContent = "🎤";
      micBtn.title = "Click to speak";
      voiceStatus.classList.remove("visible");

      if (chrome.runtime.lastError) {
        debug("Cannot inject into this tab. Open a regular webpage first.");
        return;
      }

      const result = results?.[0]?.result;
      if (!result) { debug("No result from speech recognition."); return; }
      if (result.error === "not_supported") { debug("Speech recognition not supported."); return; }
      if (result.error) { debug("Mic error: " + result.error + ". Allow mic access for this page."); return; }
      if (result.transcript) {
        inputEl.value = result.transcript;
        debug("🎤 Heard: " + result.transcript);
      }
    });
  });
}

function debug(msg) {
  const d = document.getElementById("debug");
  d.textContent = msg;
  d.style.display = "block";
}

async function sendTask() {
  const input = document.getElementById("input").value.trim();
  if (!input) {
    showError("Please type something first.");
    return;
  }

  const toolsValue = document.getElementById("tools").value;
  const availableTools = toolsValue.split(",").map(t => t.trim());

  const btn = document.getElementById("sendBtn");
  const resultBox = document.getElementById("result");
  const badge = document.getElementById("badge");
  const body = document.getElementById("resultBody");

  // Loading state
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Thinking...';
  resultBox.className = "result";
  debug("Sending to: " + MCP_URL);

  try {
    let response;
    try {
      response = await fetch(MCP_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_input: input,
          context: {
            user_role: "developer",
            source: "chrome_extension",
            app: "TaskGenie"
          },
          available_tools: availableTools
        })
      });
    } catch (networkErr) {
      debug("Network error: " + networkErr.message);
      throw new Error("Cannot reach MCP server. Is it running?\n→ python3 -m uvicorn server:app --port 8001");
    }

    debug("Got response: " + response.status);

    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`Server returned non-JSON (status ${response.status})`);
    }

    if (!response.ok) {
      throw new Error(data.detail || `Server error: ${response.status}`);
    }

    // Success or pipeline error (e.g. RAG duplicate, guardrail block)
    if (data.status === "error") {
      showError(data.message || "Pipeline blocked the request.");
      btn.disabled = false;
      btn.innerHTML = "Send Task";
      return;
    }

    badge.textContent = "✓ Task Created";
    badge.className = "badge success";

    const out = data.output || {};
    const urlHtml = out.url
      ? `<div class="field">URL: <span><a href="${out.url}" target="_blank" style="color:#6366f1">${out.url}</a></span></div>`
      : "";

    body.innerHTML = `
      <div class="field">Action: <span>${data.action_taken || "—"}</span></div>
      <div class="field">Tool used: <span>${data.tool_used || "—"}</span></div>
      <div class="field">Priority: <span>${out.priority || "—"}</span></div>
      <div class="field">Deadline: <span>${out.deadline || "No deadline"}</span></div>
      ${urlHtml}
      <div class="task-id">${out.task_id || "—"}</div>
      <div style="margin-top:8px;color:#aaa;font-size:11px">${out.summary || ""}</div>
    `;
    resultBox.className = "result success visible";

  } catch (err) {
    showError(err.message);
  }

  btn.disabled = false;
  btn.innerHTML = "Send Task";
}

function showError(msg) {
  const badge = document.getElementById("badge");
  const body = document.getElementById("resultBody");
  const resultBox = document.getElementById("result");

  badge.textContent = "✗ Error";
  badge.className = "badge error";
  body.innerHTML = `<div style="color:#ef4444;white-space:pre-wrap;font-size:11px">${msg}</div>`;
  resultBox.className = "result error visible";
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("sendBtn").addEventListener("click", sendTask);
  document.getElementById("micBtn").addEventListener("click", toggleVoice);

  document.getElementById("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendTask();
    }
  });
});
