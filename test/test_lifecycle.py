from __future__ import annotations

from types import SimpleNamespace


def test_package_import_does_not_import_http_server():
    import sys

    sys.modules.pop("infernux_mcp.server", None)
    import infernux_mcp

    assert infernux_mcp is not None
    assert "infernux_mcp.server" not in sys.modules


def test_mcp_preload_ignores_authoring_build_worker(monkeypatch):
    from infernux_mcp.lifecycle import InfernuxMCPPreload

    imported_server = False

    def fail_if_imported(name, *args, **kwargs):
        nonlocal imported_server
        if name == "infernux_mcp.server":
            imported_server = True
            raise AssertionError("build worker must not import the MCP server")
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", fail_if_imported)
    preload = InfernuxMCPPreload()
    preload.preload(
        SimpleNamespace(runtime=True, engine=None, project_root="unused")
    )

    assert not imported_server
    assert not preload._loaded
