# Unit Tests — LLM Decision Engine
# Tests decision parsing and fallback logic in mcp_core/decision.py

import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_core.decision import llm_decide, _fallback
from mcp_core.models import ActionObject


TOOLS = ["notion", "jira"]
CONTEXT = {"source": "chrome_extension", "user_role": "developer"}


class TestFallback:

    def test_fallback_returns_action_object(self):
        """_fallback should always return a valid ActionObject."""
        result = _fallback("Fix the login bug", TOOLS)
        assert isinstance(result, ActionObject)

    def test_fallback_uses_first_tool(self):
        """_fallback should use the first tool in the list."""
        result = _fallback("some task", ["jira", "notion"])
        assert result.tool == "jira"

    def test_fallback_preserves_input_in_description(self):
        """_fallback should put model_input in data.description."""
        result = _fallback("Fix the login bug", TOOLS)
        assert "Fix the login bug" in result.data["description"]

    def test_fallback_has_required_data_fields(self):
        """_fallback data should have title, description, priority, deadline."""
        result = _fallback("some task", TOOLS)
        assert "title" in result.data
        assert "description" in result.data
        assert "priority" in result.data
        assert "deadline" in result.data

    def test_fallback_action_is_create_task(self):
        """_fallback action should always be 'create_task'."""
        result = _fallback("some task", TOOLS)
        assert result.action == "create_task"


class TestLLMDecide:

    def test_no_tools_raises_value_error(self):
        """llm_decide with empty tools should raise ValueError."""
        with pytest.raises(ValueError, match="No tools"):
            llm_decide("Fix bug", CONTEXT, [])

    def test_valid_llm_response_parsed_correctly(self):
        """Valid JSON from LLM should be parsed into ActionObject."""
        mock_response = '{"action": "create_task", "tool": "jira", "data": {"title": "Fix bug", "description": "desc", "priority": "High", "deadline": "Friday"}}'
        with patch("mcp_core.decision.call_llm", return_value=mock_response):
            result = llm_decide("Fix the login bug", CONTEXT, TOOLS)
            assert isinstance(result, ActionObject)
            assert result.tool == "jira"
            assert result.action == "create_task"
            assert result.data["title"] == "Fix bug"

    def test_invalid_json_falls_back(self):
        """Unparseable LLM response should trigger fallback gracefully."""
        with patch("mcp_core.decision.call_llm", return_value="not valid json at all"):
            result = llm_decide("Fix the login bug", CONTEXT, TOOLS)
            assert isinstance(result, ActionObject)
            assert result.tool in TOOLS  # fallback uses first tool

    def test_markdown_wrapped_json_parsed(self):
        """LLM response wrapped in markdown fences should still parse."""
        mock_response = '```json\n{"action": "create_task", "tool": "notion", "data": {"title": "Write docs", "description": "d", "priority": "Low", "deadline": "None"}}\n```'
        with patch("mcp_core.decision.call_llm", return_value=mock_response):
            result = llm_decide("Write docs", CONTEXT, TOOLS)
            assert result.tool == "notion"

    def test_partial_json_falls_back(self):
        """Partial/incomplete JSON should trigger fallback."""
        with patch("mcp_core.decision.call_llm", return_value='{"action": "create_task"'):
            result = llm_decide("some task", CONTEXT, TOOLS)
            assert isinstance(result, ActionObject)

    def test_result_tool_is_in_available_tools(self):
        """Result tool should always be one of the available tools (or fallback)."""
        mock_response = '{"action": "create_task", "tool": "notion", "data": {"title": "t", "description": "d", "priority": "Medium", "deadline": "None"}}'
        with patch("mcp_core.decision.call_llm", return_value=mock_response):
            result = llm_decide("task", CONTEXT, TOOLS)
            assert result.tool in TOOLS
