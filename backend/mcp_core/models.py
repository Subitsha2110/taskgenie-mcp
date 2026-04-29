# MCP Layer 1: Context & Data Models
# Defines the shape of all data flowing through the MCP pipeline

from pydantic import BaseModel
from typing import Any, Optional


class MCPRequest(BaseModel):
    model_input: str
    context: dict[str, Any]
    available_tools: list[str]


class ActionObject(BaseModel):
    action: str
    tool: str
    data: dict[str, Any]


class MCPResponse(BaseModel):
    status: str
    action_taken: str
    tool_used: str
    output: dict[str, Any]
