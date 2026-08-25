"""MCP access to the same project plugin authority used by Editor UI."""

from __future__ import annotations

import os

from Infernux.engine.path_utils import is_path_within, resolved_path
from Infernux.plugins import InxPackage, PluginManager


def _editor_main_thread(name: str, callback, *, arguments: dict | None = None):
    """Keep plugin preload and panel work on the Editor owner thread."""
    from Infernux.engine.bootstrap import EditorBootstrap

    if EditorBootstrap.instance() is None:
        return callback()
    from infernux_mcp.tools.common import main_thread

    result = main_thread(name, callback, arguments=arguments)
    return result.get("data") if result.get("ok") else result


def register_plugin_tools(mcp, project_path: str) -> None:
    project_root = resolved_path(project_path)

    def manager() -> PluginManager:
        current = PluginManager.instance()
        if current is None or current.project_root != project_root:
            current = PluginManager.startup(project_root, runtime=False)
        return current

    def project_file(value: str, *, must_exist: bool = True) -> str:
        path = resolved_path(value if os.path.isabs(value) else os.path.join(project_root, value))
        if not is_path_within(path, project_root, allow_root=False):
            raise ValueError(f"Plugin tool path is outside the project: {value}")
        if must_exist and not os.path.exists(path):
            raise FileNotFoundError(path)
        return path

    @mcp.tool(name="plugin_list")
    def plugin_list() -> dict:
        def _list():
            authority = manager()
            return {
                "ok": True,
                "registry_path": authority.registry.path,
                "available": list(authority.registry.available()),
                "installed": list(authority.registry.installed()),
                "states": [state.snapshot() for state in authority.states.values()],
            }
        return _editor_main_thread("plugin_list", _list)

    @mcp.tool(name="plugin_panel_open")
    def plugin_panel_open() -> dict:
        from Infernux.engine.bootstrap import EditorBootstrap

        def _open():
            bootstrap = EditorBootstrap.instance()
            panel = bootstrap.window_manager.open_window("plugins") if bootstrap is not None else None
            return {"ok": panel is not None, "panel_id": "plugins"}
        return _editor_main_thread("plugin_panel_open", _open)

    @mcp.tool(name="plugin_package_open")
    def plugin_package_open(package_path: str) -> dict:
        from Infernux.engine.bootstrap import EditorBootstrap

        def _open():
            path = project_file(package_path)
            bootstrap = EditorBootstrap.instance()
            panel = bootstrap.window_manager.open_window("inxpackage_import") if bootstrap is not None else None
            if panel is None or not hasattr(panel, "open_package"):
                return {"ok": False, "panel_id": "inxpackage_import"}
            panel.open_package(path)
            return {"ok": True, "panel_id": "inxpackage_import", "package_path": path}
        return _editor_main_thread("plugin_package_open", _open, arguments={"package_path": package_path})

    @mcp.tool(name="plugin_registry_add")
    def plugin_registry_add(reference: str, source_type: str, location: str, intro: str = "", version: str = "", revision: str = "", subdirectory: str = "", package: str = "") -> dict:
        source = {"type": source_type, "location": location}
        for key, value in (("revision", revision), ("subdirectory", subdirectory), ("package", package)):
            if value:
                source[key] = value
        return _editor_main_thread(
            "plugin_registry_add",
            lambda: {"ok": True, "package": manager().registry.add_package(reference, intro=intro, source=source, version=version)},
            arguments={"reference": reference, "source_type": source_type, "location": location},
        )

    @mcp.tool(name="plugin_package_inspect")
    def plugin_package_inspect(package_path: str) -> dict:
        def _inspect():
            preview = InxPackage.inspect(project_file(package_path))
            return {"ok": True, "metadata": dict(preview.metadata), "entries": [dict(item) for item in preview.entries]}
        return _editor_main_thread("plugin_package_inspect", _inspect, arguments={"package_path": package_path})

    @mcp.tool(name="plugin_package_export")
    def plugin_package_export(source_paths: list[str], destination: str, reference: str = "", intro: str = "", version: str = "") -> dict:
        def _export():
            sources = [project_file(path) for path in source_paths]
            target = project_file(destination, must_exist=False)
            metadata = {key: value for key, value in {"reference": reference, "intro": intro, "version": version}.items() if value}
            preview = InxPackage.export(project_root, sources, target, metadata=metadata)
            return {"ok": True, "package_path": preview.package_path, "metadata": dict(preview.metadata), "entries": list(preview.project_entries)}
        return _editor_main_thread("plugin_package_export", _export, arguments={"source_paths": source_paths, "destination": destination})

    @mcp.tool(name="plugin_install_package")
    def plugin_install_package(package_path: str, selected_entries: list[str] | None = None, install_dependencies: bool = True) -> dict:
        def _install():
            state = manager().install_package(project_file(package_path), selected=selected_entries, install_dependencies=install_dependencies)
            return {"ok": state.loaded, "state": state.snapshot()}
        return _editor_main_thread("plugin_install_package", _install, arguments={"package_path": package_path, "selected_entries": selected_entries or []})

    @mcp.tool(name="plugin_install_source")
    def plugin_install_source(source_type: str, location: str, revision: str = "", subdirectory: str = "", package: str = "", install_dependencies: bool = True) -> dict:
        source = {"type": source_type, "location": location}
        for key, value in (("revision", revision), ("subdirectory", subdirectory), ("package", package)):
            if value:
                source[key] = value
        def _install():
            state = manager().install_source(source, install_dependencies=install_dependencies)
            return {"ok": state.loaded, "state": state.snapshot()}
        return _editor_main_thread("plugin_install_source", _install, arguments={"source_type": source_type, "location": location})

    @mcp.tool(name="plugin_reload")
    def plugin_reload(reference: str) -> dict:
        def _reload():
            state = manager().reload(reference)
            return {"ok": state.loaded, "state": state.snapshot()}
        return _editor_main_thread("plugin_reload", _reload, arguments={"reference": reference})

    @mcp.tool(name="plugin_set_enabled")
    def plugin_set_enabled(reference: str, enabled: bool) -> dict:
        def _set_enabled():
            state = manager().set_enabled(reference, enabled)
            return {"ok": not state.error, "state": state.snapshot()}
        return _editor_main_thread(
            "plugin_set_enabled",
            _set_enabled,
            arguments={"reference": reference, "enabled": enabled},
        )

    @mcp.tool(name="plugin_uninstall")
    def plugin_uninstall(reference: str) -> dict:
        def _uninstall():
            removed = manager().uninstall(reference)
            return {"ok": True, "removed": removed}
        return _editor_main_thread(
            "plugin_uninstall",
            _uninstall,
            arguments={"reference": reference},
        )

    @mcp.tool(name="plugin_pip_install")
    def plugin_pip_install(syntax: str) -> dict:
        return manager().install_pip(syntax)


__all__ = ["register_plugin_tools"]
