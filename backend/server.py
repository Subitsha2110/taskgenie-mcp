"""
TaskGenie — Real MCP Server + Full AI Pipeline

Architecture:
  MCP Protocol  → JSON-RPC 2.0 (tools/list, tools/call)
  Guardrails    → input + output validation
  Agentic RAG   → duplicate detection via FAISS + Notion
  LangGraph     → multi-agent pipeline (4 agents)
  Observability → structured logging + trace IDs
  Tools         → real Notion + Jira APIs

Transports:
  stdio             → Claude Desktop / Cursor
  POST /task        → Chrome Extension (REST bridge)
  /mcp-server/mcp   → MCP Inspector / any MCP client
"""

import contextlib
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from agents.graph import run_pipeline
from tools.notion import create_notion_task
from tools.jira import create_jira_task
from rag.retriever import rebuild_index

TOOLS = {
    "notion": create_notion_task,
    "jira":   create_jira_task,
}

# ── Real MCP Server ────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="TaskGenie MCP Server",
    stateless_http=True,
    json_response=True,
)


# ── MCP Tool 1: Notion ────────────────────────────────────────────────────────
@mcp.tool()
def notion_create_task(title: str, description: str, priority: str, deadline: str) -> dict:
    """Create a task directly in Notion."""
    return create_notion_task({"title": title, "description": description,
                               "priority": priority, "deadline": deadline})


# ── MCP Tool 2: Jira ──────────────────────────────────────────────────────────
@mcp.tool()
def jira_create_task(title: str, description: str, priority: str, deadline: str) -> dict:
    """Create an issue directly in Jira."""
    return create_jira_task({"title": title, "description": description,
                             "priority": priority, "deadline": deadline})


# ── MCP Tool 3: Smart route — full pipeline ───────────────────────────────────
@mcp.tool()
def smart_route_task(
    model_input: str,
    user_role: str = "developer",
    source: str = "mcp_client",
    available_tools: str = "notion,jira",
) -> dict:
    """
    Full AI pipeline:
    1. Guardrails validate input
    2. RAG checks for duplicate tasks
    3. Groq LLM decides action + tool
    4. Tool executes (Notion or Jira)
    Returns structured result with trace_id for observability.
    available_tools: comma-separated e.g. 'notion,jira'
    """
    tools = [t.strip() for t in available_tools.split(",")]
    context = {"normalized_input": model_input.lower(),
               "user_role": user_role, "source": source}
    return run_pipeline(model_input=model_input, context=context, tools=tools)


# ── FastAPI app ────────────────────────────────────────────────────────────────
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="TaskGenie MCP Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Real MCP protocol endpoint
app.mount("/mcp-server", mcp.streamable_http_app())


# ── REST bridge for Chrome Extension ──────────────────────────────────────────
class ExtensionRequest(BaseModel):
    model_input: str
    context: dict[str, Any] = {}
    available_tools: list[str] = ["notion", "jira"]


@app.post("/task")
def extension_bridge(req: ExtensionRequest) -> dict:
    """
    Chrome Extension entry point.
    Runs the full LangGraph multi-agent pipeline.
    """
    tools = req.available_tools
    context = {
        "normalized_input": req.model_input.lower(),
        "user_role": req.context.get("user_role", "developer"),
        "source": req.context.get("source", "chrome_extension"),
    }
    result = run_pipeline(model_input=req.model_input, context=context, tools=tools)
    # Rebuild RAG index after successful task creation so next request is up to date
    if result.get("status") == "success":
        rebuild_index()
    return result


# ── stdio entry point (Claude Desktop / Cursor) ───────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
