# Observability Layer — Structured logging + request tracing
# Every request gets a trace_id. Every layer logs with that id.
# This gives full visibility into: input → LLM → tool → output

import logging
import time
import uuid
from typing import Any

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("taskgenie")


def new_trace_id() -> str:
    """Generate a unique trace ID for each request."""
    return str(uuid.uuid4())[:8]


def log_request(trace_id: str, model_input: str, tools: list[str], context: dict):
    logger.info(f"[{trace_id}] REQUEST input='{model_input}' tools={tools} context={context}")


def log_llm_call(trace_id: str, prompt_len: int, response: str, duration_ms: float):
    logger.info(f"[{trace_id}] LLM prompt_chars={prompt_len} response='{response[:80]}...' duration={duration_ms:.0f}ms")


def log_tool_call(trace_id: str, tool: str, action: str, data: dict):
    logger.info(f"[{trace_id}] TOOL tool={tool} action={action} title='{data.get('title', '')}'")


def log_response(trace_id: str, status: str, tool_used: str, task_id: Any, duration_ms: float):
    logger.info(f"[{trace_id}] RESPONSE status={status} tool={tool_used} task_id={task_id} total={duration_ms:.0f}ms")


def log_error(trace_id: str, layer: str, error: str):
    logger.error(f"[{trace_id}] ERROR layer={layer} error='{error}'")


def log_guardrail(trace_id: str, check: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "BLOCK"
    logger.info(f"[{trace_id}] GUARDRAIL [{status}] check={check} detail='{detail}'")
