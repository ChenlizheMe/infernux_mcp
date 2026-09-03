"""Verified loopback client transport for Supervisor-driven MCP sessions."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any
from urllib.parse import urlparse


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})


def create_loopback_client(endpoint: str, *, timeout_seconds: float | None = None):
    """Create a FastMCP client that never inherits remote proxy settings.

    Supervisor sessions deliberately bind to loopback. Disabling inherited HTTP
    environment settings prevents remote-desktop proxy configuration from
    redirecting local MCP traffic away from the Editor.
    """
    parsed = urlparse(str(endpoint or ""))
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS or not parsed.path:
        raise ValueError("Loopback MCP client requires an http://127.0.0.1 or http://localhost endpoint.")

    import httpx
    from fastmcp import Client
    from fastmcp.client.transports.http import StreamableHttpTransport

    def http_client_factory(headers=None, auth=None, follow_redirects=True, timeout=None):
        return httpx.AsyncClient(
            headers=headers,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout or httpx.Timeout(30.0, read=300.0),
            trust_env=False,
        )

    transport = StreamableHttpTransport(str(endpoint), httpx_client_factory=http_client_factory)
    return Client(transport, timeout=timeout_seconds)


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


async def _run_cli(args: argparse.Namespace) -> Any:
    async with create_loopback_client(args.endpoint, timeout_seconds=args.timeout) as client:
        if args.command in {"list-tools", "describe"}:
            tools = list(await client.list_tools())
            if args.command == "describe":
                matches = [tool for tool in tools if tool.name == args.tool]
                if not matches:
                    raise ValueError(f"MCP tool not found: {args.tool}")
                return _json_value(matches[0])
            query = str(args.match or "").casefold()
            if query:
                tools = [tool for tool in tools if query in tool.name.casefold()]
            return _json_value(tools)
        tool_args = json.loads(args.args)
        if not isinstance(tool_args, dict):
            raise ValueError("--args must decode to a JSON object")
        return _json_value((await client.call_tool(args.tool, tool_args)).data)


def main(argv: list[str] | None = None) -> int:
    """Run a proxy-safe, machine-readable client for loopback Editor MCP sessions."""
    parser = argparse.ArgumentParser(prog="infernux-mcp")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9713/mcp")
    parser.add_argument("--timeout", type=float, default=30.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_tools = subparsers.add_parser("list-tools")
    list_tools.add_argument("--match", default="")
    describe = subparsers.add_parser("describe")
    describe.add_argument("tool")
    call = subparsers.add_parser("call")
    call.add_argument("tool")
    call.add_argument("--args", default="{}")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(asyncio.run(_run_cli(args)), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
