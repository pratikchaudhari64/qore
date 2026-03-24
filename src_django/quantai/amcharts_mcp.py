import json
import requests

MCP_URL = "http://localhost:3100/mcp"
_req_id = 0


def _parse_sse(text: str) -> dict:
    """Extract JSON payload from an SSE response (data: {...} lines)."""
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return json.loads(text)


def _call_mcp(method: str, params: dict = None) -> dict:
    global _req_id
    _req_id += 1
    resp = requests.post(
        MCP_URL,
        json={"jsonrpc": "2.0", "method": method, "params": params or {}, "id": _req_id},
        headers={"Accept": "application/json, text/event-stream"},
        timeout=30,
    )
    return _parse_sse(resp.text).get("result", {})


def list_tools() -> list:
    """Return list of tool definitions from the amCharts MCP service."""
    return _call_mcp("tools/list").get("tools", [])


def call_tool(tool_name: str, arguments: dict) -> str:
    """Call a named tool and return its text content."""
    result = _call_mcp("tools/call", {"name": tool_name, "arguments": arguments})
    contents = result.get("content", [])
    return "\n\n".join(c.get("text", "") for c in contents if c.get("type") == "text")
