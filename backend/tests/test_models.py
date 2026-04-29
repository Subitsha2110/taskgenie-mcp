# Unit Tests — Pydantic Models
# Tests data model validation in mcp_core/models.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_core.models import MCPRequest, ActionObject, MCPResponse


class TestMCPRequest:

    def test_valid_request(self):
        """MCPRequest should accept valid fields."""
        req = MCPRequest(
            model_input="Fix the login bug",
            context={"source": "chrome_extension"},
            available_tools=["notion", "jira"]
        )
        assert req.model_input == "Fix the login bug"
        assert req.available_tools == ["notion", "jira"]

    def test_empty_context_allowed(self):
        """Empty context dict should be valid."""
        req = MCPRequest(model_input="task", context={}, available_tools=["notion"])
        assert req.context == {}

    def test_empty_tools_list_allowed(self):
        """Empty tools list is structurally valid (guardrails handle logic)."""
        req = MCPRequest(model_input="task", context={}, available_tools=[])
        assert req.available_tools == []


class TestActionObject:

    def test_valid_action_object(self):
        """ActionObject should accept valid fields."""
        obj = ActionObject(
            action="create_task",
            tool="notion",
            data={"title": "Fix bug", "priority": "High"}
        )
        assert obj.action == "create_task"
        assert obj.tool == "notion"
        assert obj.data["title"] == "Fix bug"

    def test_data_can_be_empty_dict(self):
        """data field can be an empty dict structurally."""
        obj = ActionObject(action="create_task", tool="jira", data={})
        assert obj.data == {}

    def test_data_preserves_all_fields(self):
        """All data fields should be preserved as-is."""
        data = {
            "title": "Deploy fix",
            "description": "Deploy the hotfix to prod",
            "priority": "High",
            "deadline": "today"
        }
        obj = ActionObject(action="create_task", tool="jira", data=data)
        assert obj.data == data


class TestMCPResponse:

    def test_valid_response(self):
        """MCPResponse should accept valid fields."""
        resp = MCPResponse(
            status="success",
            action_taken="create_task",
            tool_used="notion",
            output={"task_id": "abc123", "message": "Created"}
        )
        assert resp.status == "success"
        assert resp.tool_used == "notion"

    def test_error_status(self):
        """MCPResponse should accept error status."""
        resp = MCPResponse(
            status="error",
            action_taken="none",
            tool_used="none",
            output={"error": "Guardrail blocked"}
        )
        assert resp.status == "error"
