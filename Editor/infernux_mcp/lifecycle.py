"""Generic InxPreload lifecycle for the default MCP Host service."""

from __future__ import annotations

import os

from Infernux.lifecycle import InxPreload, PreloadContext


class InfernuxMCPPreload(InxPreload):
    def __init__(self) -> None:
        self._loaded = False

    def preload(self, context: PreloadContext) -> None:
        if context.runtime:
            return
        from infernux_mcp.server import start_server

        host = os.environ.get("INFERNUX_MCP_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = int(os.environ.get("INFERNUX_MCP_PORT", "9713"))
        if not start_server(context.project_root, host=host, port=port):
            raise RuntimeError("Infernux MCP server did not start")
        self._loaded = True

    def unload(self) -> None:
        if not self._loaded:
            return
        from infernux_mcp.server import stop_server

        stop_server()
        self._loaded = False


__all__ = ["InfernuxMCPPreload"]
