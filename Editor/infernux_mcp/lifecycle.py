"""Generic InxPreload lifecycle for the default MCP Host service."""

from __future__ import annotations

import os
import threading

from Infernux.lifecycle import InxPreload, PreloadContext


class InfernuxMCPPreload(InxPreload):
    def __init__(self) -> None:
        self._loaded = False
        self._starter: threading.Thread | None = None

    def preload(self, context: PreloadContext) -> None:
        if context.runtime:
            return

        project_root = context.project_root
        host = os.environ.get("INFERNUX_MCP_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = int(os.environ.get("INFERNUX_MCP_PORT", "9713"))

        # The FastMCP/starlette/uvicorn import chain plus the server readiness
        # wait is the single heaviest piece of editor plugin preload, and the
        # splash screen sits on "Preloading project plugins…" for all of it.
        # Nothing at startup depends on the HTTP endpoint being reachable
        # before the first client connects, so bring it up off-thread and let
        # a failure surface in the log instead of blocking the editor.
        def _start() -> None:
            try:
                from infernux_mcp.server import start_server

                if not start_server(project_root, host=host, port=port):
                    raise RuntimeError("Infernux MCP server did not start")
            except Exception as exc:
                from Infernux.debug import Debug

                Debug.log_error(f"Infernux MCP server failed to start: {exc}")

        self._starter = threading.Thread(
            target=_start, name="InfernuxMCPStart", daemon=True
        )
        self._starter.start()
        self._loaded = True

    def unload(self) -> None:
        if not self._loaded:
            return
        starter = self._starter
        if starter is not None:
            starter.join(timeout=10.0)
            self._starter = None
        from infernux_mcp.server import stop_server

        stop_server()
        self._loaded = False


__all__ = ["InfernuxMCPPreload"]
