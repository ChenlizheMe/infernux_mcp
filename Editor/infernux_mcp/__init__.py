"""Embedded MCP integration for Infernux Editor."""

from infernux_mcp.capabilities import current_config
from infernux_mcp.server import endpoint_url, health_url, is_running, start_server, stop_server

__all__ = ["current_config", "endpoint_url", "health_url", "is_running", "start_server", "stop_server"]
