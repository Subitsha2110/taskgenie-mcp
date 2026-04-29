# Unit Tests — Context Layer
# Tests context enrichment logic in mcp_core/context.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_core.context import build_context


class TestBuildContext:

    def test_basic_context_structure(self):
        """build_context should return all required keys."""
        result = build_context(
            model_input="Fix the login bug",
            context={"user_role": "developer", "source": "chrome_extension"},
            available_tools=["notion", "jira"]
        )
        assert "raw_input" in result
        assert "normalized_input" in result
        assert "user_role" in result
        assert "source" in result
        assert "available_tools" in result

    def test_raw_input_preserved(self):
        """raw_input should be the original unmodified string."""
        result = build_context("Fix the Login Bug", {}, ["notion"])
        assert result["raw_input"] == "Fix the Login Bug"

    def test_normalized_input_is_lowercase_stripped(self):
        """normalized_input should be lowercased and stripped."""
        result = build_context("  Fix the Login Bug  ", {}, ["notion"])
        assert result["normalized_input"] == "fix the login bug"

    def test_user_role_from_context(self):
        """user_role should be pulled from context dict."""
        result = build_context("task", {"user_role": "admin"}, ["notion"])
        assert result["user_role"] == "admin"

    def test_user_role_defaults_to_unknown(self):
        """user_role should default to 'unknown' if not provided."""
        result = build_context("task", {}, ["notion"])
        assert result["user_role"] == "unknown"

    def test_source_from_context(self):
        """source should be pulled from context dict."""
        result = build_context("task", {"source": "mcp_client"}, ["notion"])
        assert result["source"] == "mcp_client"

    def test_source_defaults_to_unknown(self):
        """source should default to 'unknown' if not provided."""
        result = build_context("task", {}, ["notion"])
        assert result["source"] == "unknown"

    def test_available_tools_passed_through(self):
        """available_tools should be included in the context."""
        tools = ["notion", "jira"]
        result = build_context("task", {}, tools)
        assert result["available_tools"] == tools

    def test_empty_context_dict(self):
        """Empty context dict should not raise — defaults should apply."""
        result = build_context("Create a task", {}, ["notion"])
        assert result["user_role"] == "unknown"
        assert result["source"] == "unknown"
        assert result["app"] == "unknown"

    def test_app_from_context(self):
        """app field should be pulled from context dict."""
        result = build_context("task", {"app": "taskgenie"}, ["notion"])
        assert result["app"] == "taskgenie"
