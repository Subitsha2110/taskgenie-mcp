# MCP Layer 3: Action Execution Engine
# Reads the ActionObject from the decision layer,
# looks up the correct tool in the registry, and executes it.

from typing import Any
from mcp_core.models import ActionObject
from tools.notion import create_notion_task
from tools.jira import create_jira_task


# Tool Registry — maps tool name → callable
# Add new tools here without touching any other layer
TOOLS: dict[str, Any] = {
    "notion": create_notion_task,
    "jira": create_jira_task,
}


def execute_action(action_obj: ActionObject) -> dict[str, Any]:
    """
    Action execution engine.
    Resolves the tool from the registry and calls it with the action data.

    Args:
        action_obj: structured ActionObject from the decision layer

    Returns:
        Raw tool output dict

    Raises:
        ValueError: if the requested tool is not registered
    """
    tool_name = action_obj.tool

    if tool_name not in TOOLS:
        raise ValueError(f"Tool '{tool_name}' is not registered. Available: {list(TOOLS.keys())}")

    tool_fn = TOOLS[tool_name]
    return tool_fn(action_obj.data)
