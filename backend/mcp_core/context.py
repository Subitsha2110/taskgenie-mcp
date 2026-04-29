# MCP Layer 1: Context Layer
# Responsible for parsing and enriching raw input into structured context
# before it reaches the model decision layer.

from typing import Any


def build_context(model_input: str, context: dict[str, Any], available_tools: list[str]) -> dict[str, Any]:
    """
    Normalizes and enriches the incoming request into a unified context object.
    This is what the model decision layer will reason over.
    """
    return {
        "raw_input": model_input,
        "normalized_input": model_input.lower().strip(),
        "user_role": context.get("user_role", "unknown"),
        "source": context.get("source", "unknown"),
        "app": context.get("app", "unknown"),
        "available_tools": available_tools,
    }
