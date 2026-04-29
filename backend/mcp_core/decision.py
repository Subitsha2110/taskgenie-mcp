# MCP Layer 2: LLM Decision Engine
# Sends enriched context to Groq LLM and parses its JSON decision.
# The LLM dynamically decides: action, tool, and task data.

import json
from typing import Any

from mcp_core.models import ActionObject
from mcp_core.groq_client import call_llm


# Prompt template — instructs the LLM to return ONLY valid JSON
DECISION_PROMPT = """You are an MCP decision engine.
Your job:
- Decide action
- Select tool from available_tools
- Generate structured task data

Return ONLY valid JSON. Do NOT include explanations, markdown, or code blocks.

Format:
{{
  "action": "create_task",
  "tool": "<must be one of available_tools>",
  "data": {{
    "title": "...",
    "description": "...",
    "priority": "High/Medium/Low",
    "deadline": "..."
  }}
}}

Input: {model_input}
Context: {context}
Available Tools: {available_tools}"""


def _fallback(model_input: str, tools: list[str]) -> ActionObject:
    """
    Fallback ActionObject when LLM returns invalid or unparseable JSON.
    Ensures the pipeline never crashes due to LLM output issues.
    """
    return ActionObject(
        action="create_task",
        tool=tools[0],
        data={
            "title": "Fallback Task",
            "description": model_input,
            "priority": "Medium",
            "deadline": "None",
        },
    )


def llm_decide(model_input: str, context: dict[str, Any], tools: list[str]) -> ActionObject:
    """
    Core LLM decision function.

    1. Builds a structured prompt with full context
    2. Calls Groq LLM
    3. Parses JSON response into an ActionObject
    4. Falls back gracefully on any parse failure

    Args:
        model_input: raw user instruction
        context: enriched context dict
        tools: list of available tool names

    Returns:
        ActionObject with action, tool, and structured data
    """
    if not tools:
        raise ValueError("No tools available for action execution")

    # Build the prompt
    prompt = DECISION_PROMPT.format(
        model_input=model_input,
        context=json.dumps(context, indent=2),
        available_tools=tools,
    )

    # Call Groq LLM
    raw_response = call_llm(prompt)

    # Parse LLM JSON output — fall back on any failure
    try:
        # Strip markdown code fences if LLM wraps output despite instructions
        cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(cleaned)

        return ActionObject(
            action=parsed["action"],
            tool=parsed["tool"],
            data=parsed["data"],
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        # LLM returned something unparseable — use fallback
        return _fallback(model_input, tools)
