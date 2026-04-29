# Unit Tests — Executor Layer
# Tests tool registry and execution logic in mcp_core/executor.py

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_core.executor import execute_action, TOOLS
from mcp_core.models import ActionObject


class TestExecuteAction:

    def _make_action(self, tool: str) -> ActionObject:
        return ActionObject(
            action="create_task",
            tool=tool,
            data={
                "title": "Test Task",
                "description": "Test description",
                "priority": "Medium",
                "deadline": "Friday"
            }
        )

    def test_notion_tool_registered(self):
        """notion should be in the TOOLS registry."""
        assert "notion" in TOOLS

    def test_jira_tool_registered(self):
        """jira should be in the TOOLS registry."""
        assert "jira" in TOOLS

    def test_unknown_tool_raises_value_error(self):
        """Requesting an unregistered tool should raise ValueError."""
        action = self._make_action("slack")
        with pytest.raises(ValueError, match="not registered"):
            execute_action(action)

    def test_execute_notion_calls_correct_function(self):
        """execute_action with notion should call the notion tool function."""
        mock_result = {"task_id": "notion-123", "message": "Created"}
        mock_fn = MagicMock(return_value=mock_result)
        with patch.dict("mcp_core.executor.TOOLS", {"notion": mock_fn}):
            action = self._make_action("notion")
            result = execute_action(action)
            mock_fn.assert_called_once_with(action.data)
            assert result == mock_result

    def test_execute_jira_calls_correct_function(self):
        """execute_action with jira should call the jira tool function."""
        mock_result = {"task_id": "KAN-42", "message": "Issue created"}
        mock_fn = MagicMock(return_value=mock_result)
        with patch.dict("mcp_core.executor.TOOLS", {"jira": mock_fn}):
            action = self._make_action("jira")
            result = execute_action(action)
            mock_fn.assert_called_once_with(action.data)
            assert result == mock_result

    def test_execute_passes_data_correctly(self):
        """execute_action should pass action.data to the tool function."""
        captured = {}

        def fake_tool(data):
            captured["data"] = data
            return {"task_id": "x1", "message": "ok"}

        with patch.dict("mcp_core.executor.TOOLS", {"notion": fake_tool}):
            action = self._make_action("notion")
            execute_action(action)
            assert captured["data"]["title"] == "Test Task"
            assert captured["data"]["priority"] == "Medium"

    def test_error_message_includes_tool_name(self):
        """ValueError message should mention the bad tool name."""
        action = self._make_action("unknown_tool")
        with pytest.raises(ValueError, match="unknown_tool"):
            execute_action(action)
