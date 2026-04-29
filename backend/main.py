# MCP Server — FastAPI entry point
# Pipeline:
#   1. Context Layer   → build_context()
#   2. LLM Decision    → llm_decide()   [Groq: llama-4-scout]
#   3. Execution Layer → execute_action()
#   4. Tool Layer      → tools/notion.py | tools/jira.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp_core.models import MCPRequest, MCPResponse
from mcp_core.context import build_context
from mcp_core.decision import llm_decide
from mcp_core.executor import execute_action

app = FastAPI(title="MCP Server (Groq)", description="Model Context Protocol server powered by Groq LLM")

# Allow Chrome extension to call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.post("/mcp", response_model=MCPResponse)
def mcp_endpoint(request: MCPRequest) -> MCPResponse:
    # Layer 1: Enrich raw input into structured context
    context = build_context(
        model_input=request.model_input,
        context=request.context,
        available_tools=request.available_tools,
    )

    # Layer 2: LLM decides action + tool + data
    try:
        action_obj = llm_decide(
            model_input=request.model_input,
            context=context,
            tools=request.available_tools,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Layer 3 + 4: Execute via tool registry
    try:
        tool_output = execute_action(action_obj)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return MCPResponse(
        status="success",
        action_taken=action_obj.action,
        tool_used=action_obj.tool,
        output=tool_output,
    )
