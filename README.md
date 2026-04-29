# ⚡ TaskGenie MCP

> **An intelligent task management system powered by Model Context Protocol, LangGraph multi-agent orchestration, and Agentic RAG — that thinks before it acts.**

TaskGenie doesn't just create tasks. It *reasons* about them. Every request passes through a 4-agent AI pipeline that validates safety, checks for duplicates, decides the best tool, and executes — all autonomously.

---

## 🎯 What Problem Does It Solve?

Developers and teams waste time manually triaging tasks — deciding whether a bug goes to Jira, a note goes to Notion, checking if the task already exists, setting priorities. TaskGenie automates all of that with AI.

**You describe the task. TaskGenie handles the rest.**

- Highlight text on any webpage → right-click → task created in the right tool
- AI decides: Jira for bugs, Notion for docs/features
- AI extracts: priority, deadline, title, description
- AI checks: is this task a duplicate of something already in your system?

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   Chrome Extension          MCP Clients (Claude / Cursor)       │
│   (popup + context menu)    (JSON-RPC 2.0)                      │
└──────────────────┬──────────────────────────┬───────────────────┘
                   │  POST /task              │  /mcp-server/mcp
                   ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MCP SERVER  (server.py)                     │
│              FastAPI + FastMCP (JSON-RPC 2.0 bridge)            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              LANGGRAPH MULTI-AGENT PIPELINE                     │
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │ GuardrailAgent│───▶│   RAGAgent   │───▶│ RouterAgent  │     │
│   │  (Safety LLM) │    │(Duplicate LLM│    │ (Decision LLM│     │
│   └──────────────┘    └──────────────┘    └──────┬───────┘     │
│          │ blocked           │ duplicate          │             │
│          ▼                   ▼                    ▼             │
│         END                 END           ┌──────────────┐      │
│                                           │ExecutorAgent │      │
│                                           │ (Action LLM) │      │
│                                           └──────┬───────┘      │
└──────────────────────────────────────────────────┼──────────────┘
                                                   │
                               ┌───────────────────┴──────────────┐
                               │                                  │
                               ▼                                  ▼
                        ┌─────────────┐                  ┌──────────────┐
                        │  Notion API │                  │   Jira API   │
                        │  (Pages DB) │                  │  (Issues)    │
                        └─────────────┘                  └──────────────┘
```

---

## 🧠 Concepts Implemented

### 1. MCP — Model Context Protocol

**What it is:** MCP is an open standard by Anthropic that lets AI assistants (like Claude) connect to external tools and data sources through a standardized JSON-RPC 2.0 interface. Think of it as USB-C for AI — one protocol, any tool.

**How we implemented it:**
- Built a real MCP server using the official `mcp` Python SDK with `FastMCP`
- Exposes 3 tools: `notion_create_task`, `jira_create_task`, `smart_route_task`
- Any MCP-compatible client (Claude Desktop, Cursor, MCP Inspector) can connect and call these tools
- Runs on `http://localhost:8001/mcp-server/mcp`

```python
# server.py — Real MCP tool registration
@mcp.tool()
def smart_route_task(task_description: str) -> dict:
    """Full AI pipeline — LLM decides tool, priority, deadline."""
    return run_pipeline(task_description, context={}, tools=["notion", "jira"])
```

---

### 2. Agentic RAG — Retrieval-Augmented Generation

**What it is:** RAG enhances AI responses by first retrieving relevant existing data before generating output. In our case, we retrieve existing tasks to prevent duplicates — making the AI *aware* of what already exists before creating anything new.

**How we implemented it:**
- All existing Notion tasks are embedded using `sentence-transformers` (`all-MiniLM-L6-v2`)
- Embeddings are stored in a **FAISS** vector index on disk (`rag/index.faiss`)
- Every new task request is embedded and compared against the index
- Cosine similarity score determines if it's a duplicate (threshold: 0.85)
- A dedicated **RAGAgent** (LLM) then *reasons* about the similarity score and decides whether to proceed

```
New Task: "Fix authentication bug"
    ↓ embed
[0.23, 0.87, 0.12, ...]
    ↓ FAISS search
Most similar: "Fix login bug" — similarity: 0.91
    ↓ RAGAgent LLM reasons
"Similarity > 0.90 and tasks are clearly the same → BLOCK"
```

**Why it's agentic:** The RAG result doesn't automatically block — an LLM agent *reasons* about it, considering context. A score of 0.88 might still proceed if the tasks are clearly different in scope.

---

### 3. Agentic Framework — LangGraph

**What it is:** An agentic framework gives AI the ability to take multi-step actions, make decisions, and use tools autonomously. LangGraph extends LangChain with a graph-based state machine for orchestrating complex agent workflows.

**How we implemented it:**
- Built a `StateGraph` with 4 nodes (agents), each being a real LLM call
- Shared `AgentState` (TypedDict) flows through the graph, accumulating decisions
- Conditional edges enable early exit — if guardrail blocks, the graph ends immediately without wasting LLM calls
- The graph is compiled once at startup and reused for every request

```python
graph.set_entry_point("guardrail")
graph.add_conditional_edges("guardrail", after_guardrail,
                             {"rag_check": "rag_check", "end": END})
graph.add_conditional_edges("rag_check", after_rag,
                             {"route": "route", "end": END})
graph.add_edge("route", "execute")
graph.add_edge("execute", END)
```

---

### 4. Multi-Agent System

**What it is:** Instead of one monolithic LLM prompt doing everything, we split responsibilities across specialized agents. Each agent has a focused role, its own system prompt, and its own LLM call — making the system more reliable, debuggable, and explainable.

**Our 4 agents:**

| Agent | Role | LLM Decision |
|---|---|---|
| **GuardrailAgent** | Safety checker | `{"passed": true/false, "reason": "..."}` |
| **RAGAgent** | Duplicate detector | `{"proceed": true/false, "duplicate_task": "..."}` |
| **RouterAgent** | Task classifier | `{"tool": "jira/notion", "priority": "High", "deadline": "Friday"}` |
| **ExecutorAgent** | Action + summarizer | `{"summary": "Task created successfully..."}` |

Each agent's decision is visible in the final response under the `agents` key — full transparency into the reasoning chain.

---

### 5. Guardrails

**What it is:** Guardrails are safety and validation layers that prevent bad inputs from reaching the LLM and bad outputs from reaching external tools. They act as checkpoints at every stage of the pipeline.

**Two layers of guardrails:**

**Input Guardrails** (before LLM):
- Rejects empty or whitespace-only input
- Rejects input shorter than 5 characters
- Detects prompt injection patterns (`"ignore previous instructions"`, `"jailbreak"`, `"you are now"`, etc.)
- Validates at least one tool is available

**Output Guardrails** (after LLM, before tool execution):
- Ensures LLM returned all required fields (`action`, `tool`, `data`)
- Validates the chosen tool is in the available tools list
- Ensures task title is not empty

```python
# guardrails/validator.py
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"forget everything",
    r"you are now",
    r"jailbreak",
    r"system prompt",
]
```

---

### 6. Observability — Logging & Tracing

**What it is:** Observability is the ability to understand what's happening inside your system at runtime. In AI systems, this is critical — you need to know which agent made which decision, how long each LLM call took, and where failures occurred.

**How we implemented it:**
- Every request gets a unique **trace ID** (8-char UUID) generated at entry
- Every layer logs with that trace ID — creating a full audit trail
- Structured log format: `timestamp | level | logger | [trace_id] event details`
- Logs cover: incoming request, each LLM call (with duration in ms), tool execution, final response, and errors

```
2025-04-29 10:23:11 | INFO | taskgenie | [a1c24c11] REQUEST input='Fix login bug' tools=['notion', 'jira']
2025-04-29 10:23:11 | INFO | taskgenie | [a1c24c11] LLM prompt_chars=312 response='[GuardrailAgent]...' duration=487ms
2025-04-29 10:23:12 | INFO | taskgenie | [a1c24c11] TOOL jira action=create_task title='Fix login bug'
2025-04-29 10:23:12 | INFO | taskgenie | [a1c24c11] RESPONSE status=success tool=jira task_id=KAN-7 duration=1243ms
```

---

## 📁 Project Structure

```
taskgenie-mcp/
│
├── README.md
│
├── backend/
│   ├── server.py                      # MCP server + FastAPI REST bridge
│   ├── main.py                        # Legacy REST entry point
│   ├── requirements.txt               # All dependencies
│   ├── .env.example                   # ← Credentials for evaluators
│   │
│   ├── agents/
│   │   └── graph.py                   # LangGraph 4-agent pipeline
│   │
│   ├── mcp_core/
│   │   ├── models.py                  # Pydantic request/response models
│   │   ├── context.py                 # Context enrichment layer
│   │   ├── decision.py                # LLM decision engine + fallback
│   │   ├── executor.py                # Tool registry + execution engine
│   │   └── groq_client.py             # Groq LLM client wrapper
│   │
│   ├── tools/
│   │   ├── notion.py                  # Notion API integration
│   │   └── jira.py                    # Jira REST API v3 integration
│   │
│   ├── rag/
│   │   ├── retriever.py               # FAISS search + duplicate detection
│   │   └── store.py                   # Index builder — embeds Notion tasks
│   │
│   ├── guardrails/
│   │   └── validator.py               # Input + output validation
│   │
│   ├── tracing/
│   │   └── logger.py                  # Structured logging + trace IDs
│   │
│   └── tests/
│       ├── conftest.py                # Pytest configuration
│       ├── test_guardrails.py         # 20 tests — validation logic
│       ├── test_context.py            # 10 tests — context enrichment
│       ├── test_executor.py           # 7 tests  — tool execution
│       ├── test_models.py             # 8 tests  — Pydantic models
│       ├── test_decision.py           # 11 tests — LLM decision + fallback
│       └── test_pipeline_integration.py  # 7 tests — full pipeline flow
│
└── chrome-extension/
    ├── manifest.json                  # Manifest V3 config
    ├── background.js                  # Service worker + context menu
    ├── popup.html                     # Extension UI
    └── popup.js                       # API communication
```

---

## 🚀 Setup & Running

### 1. Clone the repo
```bash
git clone https://github.com/Subitsha2110/taskgenie-mcp.git
cd taskgenie-mcp
```

### 2. Install dependencies
```bash
pip3 install -r backend/requirements.txt
```

### 3. Configure environment
```bash
cp backend/.env.example backend/.env
```
> ✅ Credentials are already filled in `.env.example` — just copy the file, no edits needed.

### 4. Start the server
```bash
cd backend
python3 -m uvicorn server:app --reload --port 8001
```

Server runs at `http://localhost:8001`

### 5. Run the test suite
```bash
cd backend
python3 -m pytest tests/ -v
```

Expected: **63 tests passing**

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/task` | POST | REST bridge — Chrome Extension entry point |
| `/mcp-server/mcp` | POST | MCP JSON-RPC 2.0 endpoint |
| `/health` | GET | Health check |

### Example Request
```bash
curl -X POST http://localhost:8001/task \
  -H "Content-Type: application/json" \
  -d '{"model_input": "Fix the login bug — users cannot authenticate", "context": {}, "available_tools": ["notion", "jira"]}'
```

### Example Response
```json
{
  "status": "success",
  "action_taken": "create_task",
  "tool_used": "jira",
  "output": {
    "task_id": "KAN-7",
    "message": "Issue created successfully in Jira",
    "priority": "High",
    "deadline": "Friday"
  },
  "trace_id": "a1c24c11",
  "agents": {
    "guardrail": { "passed": true, "reason": "Clear actionable task" },
    "rag":       { "proceed": true, "reason": "No duplicate found", "similarity_score": 0.12 },
    "router":    { "action": "create_task", "tool": "jira" },
    "executor":  { "summary": "Bug fix task created in Jira with High priority." }
  }
}
```

---

## 🧩 Chrome Extension

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked** → select the `chrome-extension/` folder
4. Click the ⚡ icon in the toolbar to open the popup
5. Or: highlight any text on a webpage → right-click → **"⚡ Create Task with TaskGenie"**

---

## 🧪 Testing

63 tests across 6 files covering every layer of the system:

| File | Coverage |
|---|---|
| `test_guardrails.py` | Input validation, injection detection, output validation |
| `test_context.py` | Context enrichment, defaults, normalization |
| `test_executor.py` | Tool registry, execution routing, error handling |
| `test_models.py` | Pydantic model validation |
| `test_decision.py` | LLM parsing, fallback logic, markdown stripping |
| `test_pipeline_integration.py` | Full pipeline — success, guardrail block, RAG block, resilience |

All tests use mocks — no real API calls needed to run the test suite.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| LLM | Groq API — `meta-llama/llama-4-scout-17b-16e-instruct` |
| Agent Framework | LangGraph (StateGraph) |
| Vector Search | FAISS + sentence-transformers (`all-MiniLM-L6-v2`) |
| MCP Server | `mcp` SDK + FastMCP |
| REST API | FastAPI + Uvicorn |
| Task Tools | Notion API v1, Jira REST API v3 |
| Chrome Extension | Manifest V3, vanilla JS |
| Testing | pytest + unittest.mock |
| Validation | Pydantic v2 |

---

## 🔑 API Keys

| Key | Purpose | Get it from |
|---|---|---|
| `GROQ_API_KEY` | LLM inference | [console.groq.com](https://console.groq.com) |
| `NOTION_API_KEY` | Create Notion pages | [notion.so/my-integrations](https://www.notion.so/my-integrations) |
| `NOTION_DATABASE_ID` | Target database | From your Notion database URL |
| `JIRA_URL` | Atlassian workspace | Your Jira instance URL |
| `JIRA_EMAIL` | Auth email | Your Atlassian account |
| `JIRA_API_TOKEN` | Jira auth | [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | Target project | e.g. `KAN` |
