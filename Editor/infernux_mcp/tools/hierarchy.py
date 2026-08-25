"""Hierarchy creation MCP tools."""

from __future__ import annotations

from infernux_mcp.tools.common import main_thread


def register_hierarchy_tools(mcp) -> None:
    @mcp.tool(name="hierarchy_list_create_kinds")
    def hierarchy_list_create_kinds() -> dict:
        """List object kinds supported by hierarchy.create_object."""

        def _list():
            from Infernux.engine.hierarchy_creation_service import HierarchyCreationService
            return {"kinds": HierarchyCreationService.instance().list_create_kinds()}

        return main_thread("hierarchy_list_create_kinds", _list)

    @mcp.tool(name="hierarchy_create_object")
    def hierarchy_create_object(
        kind: str,
        parent_id: int = 0,
        name: str = "",
        select: bool = True,
    ) -> dict:
        """Create an object using the same behavior as the Hierarchy panel."""

        def _create():
            from Infernux.engine.hierarchy_creation_service import HierarchyCreationService
            return HierarchyCreationService.instance().create(
                kind,
                parent_id=int(parent_id or 0),
                name=name or None,
                select=bool(select),
            )

        return main_thread("hierarchy_create_object", _create)
