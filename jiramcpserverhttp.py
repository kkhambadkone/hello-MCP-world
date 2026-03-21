import tracemalloc
tracemalloc.start()

import asyncio
import os
import httpx
#from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP

# -----------------------------
# Configuration from environment
# -----------------------------
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")        # e.g. https://your-domain.atlassian.net
JIRA_EMAIL = os.getenv("JIRA_EMAIL")              # your email
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")      # Jira API token

def jira_headers():
    return {"Accept": "application/json", "Content-Type": "application/json"}

def jira_auth():
    return (JIRA_EMAIL, JIRA_API_TOKEN)

def to_adf(text: str) -> dict:
    """Convert plain text to Atlassian Document Format"""
    paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": line}]} for line in text.split("\n")]
    return {"type": "doc", "version": 1, "content": paragraphs}

# -----------------------------
# FastMCP server
# -----------------------------
mcp = FastMCP("jira-mcp-http")

@mcp.tool()
async def jira_create_issue(project_key: str, summary: str, description: str, issue_type: str = "Task") -> dict:
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            },
            "issuetype": {"name": issue_type}
        }
    }

    headers = {"Content-Type": "application/json"}  # ✅ correct indentation

    async with httpx.AsyncClient(timeout=30.0) as client:
        #response = await client.post(url, json=payload, headers=headers)
        response = await client.post(
            url,
            json=payload,
            headers=jira_headers(),
            auth=jira_auth()
        )
        response.raise_for_status()

        # safely parse JSON
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        return {
            "success": response.status_code in (200, 201),
            "status_code": response.status_code,
            "data": data
        }

async def main():
    # run the HTTP MCP server
    await mcp.run_http_async(host="127.0.0.1", port=8000)

if __name__ == "__main__":
    asyncio.run(main())

