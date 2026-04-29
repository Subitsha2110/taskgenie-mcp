# Integration Tests — LangGraph Multi-Agent Pipeline
# Tests the full pipeline flow with mocked LLM and tool calls.
# Verifies agent orchestration, conditional routing, and response shape.

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _guardrail_pass():
    return '{"passed": true, "reason": "Clear actionable task"}'

def _guardrail_block():
    return '{"passed": false, "reason": "Input is gibberish"}'

def _rag_proceed():
    return '{"proceed": true, "reason": "No duplicate found", "duplicate_task": null}'

def _rag_block():
    return '{"proceed": false, "reason": "Duplicate task exists", "duplicate_task": "Fix login bug"}'

def _router_notion():
    return '{"action": "create_task", "tool": "notion", "data": {"title": "Write API docs", "description": "Document the REST API", "priority": "Medium", "deadline": "Friday"}}'

def _router_jira():
    return '{"action": "create_task", "tool": "jira", "data": {"title": "Fix login bug", "description": "Users cannot log in", "priority": "High", "deadline": "today"}}'

def _executor_summary():
    return '{"summary": "Task created successfully."}'

def _rag_no_duplicate():
    return {"is_duplicate": False, "similar_task": None, "similarity_score": 0.05}

def _notion_result():
    return {"task_id": "notion-abc", "message": "Page created in Notion", "url": "https://notion.so/abc"}

def _jira_result():
    return {"task_id": "KAN-7", "message": "Issue created in Jira", "priority": "High"}


# ── Full Pipeline Tests ───────────────────────────────────────────────────────

class TestPipelineIntegration:

    @patch("agents.graph.check_duplicate", return_value=_rag_no_duplicate())
    @patch("agents.graph.execute_action", return_value=_notion_result())
    @patch("agents.graph._llm")
    def test_successful_notion_task_creation(self, mock_llm, mock_exec, mock_rag):
        """Full pipeline should succeed and return success status for a Notion task."""
        mock_llm.side_effect = [_guardrail_pass(), _rag_proceed(), _router_notion(), _executor_summary()]

        from agents.graph import run_pipeline
        result = run_pipeline(
            model_input="Write API documentation for the REST endpoints",
            context={"source": "chrome_extension"},
            tools=["notion", "jira"]
        )

        assert result["status"] == "success"
        assert result["tool_used"] == "notion"
        assert result["action_taken"] == "create_task"
        assert "trace_id" in result
        assert "agents" in result

    @patch("agents.graph.check_duplicate", return_value=_rag_no_duplicate())
    @patch("agents.graph.execute_action", return_value=_jira_result())
    @patch("agents.graph._llm")
    def test_successful_jira_task_creation(self, mock_llm, mock_exec, mock_rag):
        """Full pipeline should succeed and return success status for a Jira task."""
        mock_llm.side_effect = [_guardrail_pass(), _rag_proceed(), _router_jira(), _executor_summary()]

        from agents.graph import run_pipeline
        result = run_pipeline(
            model_input="Fix the login bug — users cannot authenticate",
            context={"source": "mcp_client"},
            tools=["notion", "jira"]
        )

        assert result["status"] == "success"
        assert result["tool_used"] == "jira"

    @patch("agents.graph._llm")
    def test_guardrail_blocks_bad_input(self, mock_llm):
        """Pipeline should return error when guardrail agent blocks input."""
        mock_llm.return_value = _guardrail_block()

        from agents.graph import run_pipeline
        result = run_pipeline(
            model_input="asdfghjkl random gibberish",
            context={},
            tools=["notion", "jira"]
        )

        assert result["status"] == "error"
        assert "guardrail" in result["message"].lower() or "blocked" in result["message"].lower()

    @patch("agents.graph.check_duplicate", return_value=_rag_no_duplicate())
    @patch("agents.graph._llm")
    def test_rag_blocks_duplicate(self, mock_llm, mock_rag):
        """Pipeline should return error when RAG agent detects a duplicate."""
        mock_llm.side_effect = [_guardrail_pass(), _rag_block()]

        from agents.graph import run_pipeline
        result = run_pipeline(
            model_input="Fix login bug",
            context={},
            tools=["notion", "jira"]
        )

        assert result["status"] == "error"
        assert "duplicate" in result["message"].lower() or "rag" in result["message"].lower()

    @patch("agents.graph.check_duplicate", return_value=_rag_no_duplicate())
    @patch("agents.graph.execute_action", return_value=_notion_result())
    @patch("agents.graph._llm")
    def test_response_contains_agent_decisions(self, mock_llm, mock_exec, mock_rag):
        """Successful response should include all agent decision details."""
        mock_llm.side_effect = [_guardrail_pass(), _rag_proceed(), _router_notion(), _executor_summary()]

        from agents.graph import run_pipeline
        result = run_pipeline("Write docs", {"source": "test"}, ["notion", "jira"])

        assert "agents" in result
        assert "guardrail" in result["agents"]
        assert "rag" in result["agents"]
        assert "router" in result["agents"]
        assert "executor" in result["agents"]

    @patch("agents.graph.check_duplicate", return_value=_rag_no_duplicate())
    @patch("agents.graph.execute_action", return_value=_notion_result())
    @patch("agents.graph._llm")
    def test_trace_id_present_in_response(self, mock_llm, mock_exec, mock_rag):
        """Every response should include a trace_id for observability."""
        mock_llm.side_effect = [_guardrail_pass(), _rag_proceed(), _router_notion(), _executor_summary()]

        from agents.graph import run_pipeline
        result = run_pipeline("Write docs", {}, ["notion", "jira"])

        assert "trace_id" in result
        assert len(result["trace_id"]) == 8  # UUID[:8]

    @patch("agents.graph.check_duplicate", side_effect=Exception("FAISS unavailable"))
    @patch("agents.graph.execute_action", return_value=_notion_result())
    @patch("agents.graph._llm")
    def test_rag_failure_does_not_crash_pipeline(self, mock_llm, mock_exec, mock_rag):
        """If RAG check throws, pipeline should continue with fallback."""
        mock_llm.side_effect = [_guardrail_pass(), _rag_proceed(), _router_notion(), _executor_summary()]

        from agents.graph import run_pipeline
        result = run_pipeline("Write docs", {}, ["notion", "jira"])

        # Should not crash — either success or graceful error
        assert result["status"] in ["success", "error"]
