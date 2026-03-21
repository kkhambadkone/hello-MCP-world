import asyncio
import httpx
import json
import argparse

MCP_URL = "http://127.0.0.1:8000/mcp"

def parse_sse(text):
    """Extract JSON from SSE response like 'data: {...}'"""
    for line in text.strip().splitlines():
        if line.startswith("data:"):
            import json
            return json.loads(line[len("data:"):].strip())
    return None

async def get_session():
    """
    Request a new session from the MCP server.
    Returns the session ID string.
    curl -X POST http://127.0.0.1:8000/mcp -H "Content-Type: application/json"   -H "Accept: application/json, text/event-stream"   -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(MCP_URL, json=payload, headers=headers)
        print(f"response: {response}")
        print(f"response.headers: {response.headers}")
        print(f"response.text: {response.text}")
        session_id = response.headers.get("mcp-session-id") 
        print(f"SESSION ID: {session_id}")
        response.raise_for_status()
        data = parse_sse(response.text)
        print(f"Response: {data}")
        return session_id

async def create_jira_ticket(project_key, summary, description, issue_type="Task",session_id=None):
    if not session_id:
        raise ValueError("session_id must be provided")
   
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "jira_create_issue",
            "arguments": {
                "project_key": project_key,
                "summary": summary,
                "description": description,
                "issue_type": issue_type
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": session_id  # Mandatory for FastMCP HTTP
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(MCP_URL, json=payload, headers=headers)
        print(response)
        response.raise_for_status()

        try:
            result = response.json()
        except json.JSONDecodeError:
            # fallback if body is empty
            result = {"raw_text": response.text}

        if "result" in result and "content" in result["result"]:
            text_field = result["result"]["content"][0]["text"]
            try:
                # parse stringified JSON into a dict
                result["result"]["content"][0]["text_parsed"] = json.loads(text_field)
            except Exception:
                result["result"]["content"][0]["text_parsed"] = text_field

        return result 

async def main(args):
    session_id = await get_session()
    print("Session ID:", session_id)
    result = await create_jira_ticket(
        project_key=args.project,
        summary=args.summary,
        description=args.description,
        issue_type=args.type,
        session_id=session_id
    )
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Jira ticket via MCP server")
    parser.add_argument("--project", required=True, help="Jira project key")
    parser.add_argument("--summary", required=True, help="Ticket summary")
    parser.add_argument("--description", required=True, help="Ticket description")
    parser.add_argument("--type", default="Task", help="Issue type (default: Task)")

    args = parser.parse_args()
    asyncio.run(main(args))
