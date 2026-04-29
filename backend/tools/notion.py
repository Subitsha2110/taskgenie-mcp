# Tool: Notion (real API)
# Creates an actual page in your Notion database.

import os
import httpx
from pathlib import Path
from dotenv import load_dotenv
from typing import Any
from datetime import date, timedelta

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

NOTION_API_KEY     = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Map natural language deadlines → ISO date
def _resolve_date(deadline: str) -> str | None:
    if not deadline or deadline.lower() in ["none", "no deadline specified", ""]:
        return None
    today = date.today()
    d = deadline.strip().lower()
    days = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
    if d == "today":
        return today.isoformat()
    if d == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if d == "next week":
        return (today + timedelta(weeks=1)).isoformat()
    if d in days:
        target = days[d]
        current = today.weekday()
        delta = (target - current) % 7 or 7
        return (today + timedelta(days=delta)).isoformat()
    # Already ISO format
    if len(d) == 10 and d[4] == "-":
        return d
    return None


def create_notion_task(data: dict[str, Any]) -> dict[str, Any]:
    """
    Creates a real task in Notion via the Pages API.
    """
    iso_date = _resolve_date(data.get("deadline", ""))

    properties: dict[str, Any] = {
        "": {                          # Notion title column has no name in this DB
            "title": [{"text": {"content": data.get("title", "Untitled")}}]
        },
        "Priority": {
            "select": {"name": data.get("priority", "Medium")}
        },
        "Description": {
            "rich_text": [{"text": {"content": data.get("description", "")}}]
        },
    }

    if iso_date:
        properties["Deadline"] = {"date": {"start": iso_date}}

    try:
        response = httpx.post(
            "https://api.notion.com/v1/pages",
            headers=HEADERS,
            json={"parent": {"database_id": NOTION_DATABASE_ID}, "properties": properties},
            timeout=10,
        )
        response.raise_for_status()
        page = response.json()
        return {
            "task_id": page["id"],
            "message": "Task created successfully in Notion",
            "tool": "notion",
            "url": page.get("url", ""),
            "title": data.get("title"),
            "priority": data.get("priority"),
            "deadline": data.get("deadline"),
        }
    except httpx.HTTPStatusError as e:
        return {
            "task_id": None,
            "message": f"Notion API error: {e.response.status_code} — {e.response.text}",
            "tool": "notion",
        }
