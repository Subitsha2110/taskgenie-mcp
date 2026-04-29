# Tool: Jira (real API)
# Creates an actual issue in your Jira project.

import os
import base64
import httpx
from pathlib import Path
from dotenv import load_dotenv
from typing import Any

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

JIRA_URL         = os.environ.get("JIRA_URL", "")
JIRA_EMAIL       = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN   = os.environ.get("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "KAN")

# Basic auth: base64(email:token)
_auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {_auth}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Jira priority names
PRIORITY_MAP = {
    "High":   "High",
    "Medium": "Medium",
    "Low":    "Low",
}


def create_jira_task(data: dict[str, Any]) -> dict[str, Any]:
    """
    Creates a real issue in Jira via the REST API v3.
    """
    priority = PRIORITY_MAP.get(data.get("priority", "Medium"), "Medium")

    payload = {
        "fields": {
            "project":     {"key": JIRA_PROJECT_KEY},
            "summary":     data.get("title", "Untitled Task"),
            "description": {
                "type":    "doc",
                "version": 1,
                "content": [{
                    "type":    "paragraph",
                    "content": [{"type": "text", "text": data.get("description", "")}]
                }]
            },
            "issuetype": {"name": "Task"},
            "priority":  {"name": priority},
        }
    }

    try:
        response = httpx.post(
            f"{JIRA_URL}/rest/api/3/issue",
            headers=HEADERS,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        issue = response.json()
        return {
            "task_id": issue["key"],
            "message": "Issue created successfully in Jira",
            "tool": "jira",
            "url": f"{JIRA_URL}/browse/{issue['key']}",
            "title": data.get("title"),
            "priority": priority,
            "deadline": data.get("deadline"),
        }
    except httpx.HTTPStatusError as e:
        return {
            "task_id": None,
            "message": f"Jira API error: {e.response.status_code} — {e.response.text}",
            "tool": "jira",
        }
