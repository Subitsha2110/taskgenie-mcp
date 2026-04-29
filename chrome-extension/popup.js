// Points to the real MCP server bridge (server.py)
const MCP_URL = "http://127.0.0.1:8001/task";

// ── Voice Input ───────────────────────────────────────────────────────────────
let recognition = null;
let isListening = false;

function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const r = new SpeechRecognition();
  r.continuous = false;       // stop after first pause
  r.interimResults = true;    // show words as they're spoken
  r.lang = "en-US";

  const micBtn      = document.getElementById("micBtn");
  const inputEl     = document.getElementById("input");
  const voiceStatus = document.getElementById("voiceStatus");

  // Show interim (live) transcript while speaking
  r.onresult = (event) => {
    let interim = "";
    let final   = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += t;
      else interim += t;
    }
    inputEl.value = final || interim;
  };

  r.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    micBtn.textContent = "⏹";
    micBtn.title = "Click to stop";
    voiceStatus.classList.add("visible");
  };

  r.onend = () => {
    isListening = false;
    micBtn.classList.remove("listening");
    micBtn.textContent = "🎤";
    micBtn.title = "Click to speak";
    voiceStatus.classList.remove("visible");
  };

  r.onerror = (event) => {
    isListening = false;
    micBtn.classList.remove("listening");
    micBtn.textContent = "🎤";
    voiceStatus.classList.remove("visible");
    if (event.error === "not-allowed") {
      debug("Microphone permission denied. Allow mic access in Chrome.");
    }
  };

  return r;
}

function toggleVoice() {
  if (!recognition) {
    recognition = initVoice();
  }
  if (!recognition) {
    debug("Voice input not supported in this browser.");
    return;
  }
  if (isListening) {
    recognition.stop();
  } else {
    recognition.start();
  }
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
