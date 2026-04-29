# Guardrails Layer
# Validates input before it reaches the LLM and output before tool execution.
# Blocks: empty input, too short, prompt injection attempts, missing LLM fields.

import re
from typing import Any
from tracing.logger import log_guardrail

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"forget everything",
    r"you are now",
    r"disregard",
    r"system prompt",
    r"jailbreak",
]


class GuardrailError(Exception):
    pass


def validate_input(trace_id: str, model_input: str, tools: list[str]) -> None:
    """
    Input guardrails — runs before LLM call.
    Raises GuardrailError if input is unsafe or invalid.
    """
    # Check 1: empty input
    if not model_input or not model_input.strip():
        log_guardrail(trace_id, "empty_input", False, "Input is empty")
        raise GuardrailError("Input cannot be empty.")

    # Check 2: too short to be meaningful
    if len(model_input.strip()) < 5:
        log_guardrail(trace_id, "too_short", False, f"len={len(model_input)}")
        raise GuardrailError("Input too short. Please describe the task.")

    # Check 3: prompt injection
    lower = model_input.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            log_guardrail(trace_id, "prompt_injection", False, f"pattern='{pattern}'")
            raise GuardrailError("Input contains disallowed content.")

    # Check 4: no tools provided
    if not tools:
        log_guardrail(trace_id, "no_tools", False, "available_tools is empty")
        raise GuardrailError("At least one tool must be specified.")

    log_guardrail(trace_id, "input_validation", True, f"input_len={len(model_input)}")


def validate_llm_output(trace_id: str, parsed: dict[str, Any], available_tools: list[str]) -> None:
    """
    Output guardrails — runs after LLM responds, before tool execution.
    Ensures LLM returned valid, safe structured data.
    """
    # Check 1: required fields present
    for field in ["action", "tool", "data"]:
        if field not in parsed:
            log_guardrail(trace_id, "missing_field", False, f"field='{field}'")
            raise GuardrailError(f"LLM output missing required field: '{field}'")

    # Check 2: tool must be one of available tools
    if parsed["tool"] not in available_tools:
        log_guardrail(trace_id, "invalid_tool", False,
                      f"tool='{parsed['tool']}' not in {available_tools}")
        raise GuardrailError(f"LLM chose unavailable tool: '{parsed['tool']}'")

    # Check 3: data must have a title
    if not parsed.get("data", {}).get("title", "").strip():
        log_guardrail(trace_id, "missing_title", False, "data.title is empty")
        raise GuardrailError("LLM output missing task title.")

    log_guardrail(trace_id, "output_validation", True,
                  f"action={parsed['action']} tool={parsed['tool']}")
