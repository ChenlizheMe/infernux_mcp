"""Concise documentation operations for the Infernux MCP package."""

from __future__ import annotations

from Infernux.host import Operation, OperationError, OperationKind, OperationRegistry

from infernux_mcp.operation_support import operation


_GUIDES = {
    "discovery": {
        "title": "Discovering operations",
        "body": "Search schemas by task or domain, fetch the selected full schema, then invoke its stable dotted operation ID through the matching query, command, or workflow gateway.",
        "tags": ("schema", "search", "gateway", "operation"),
    },
    "assets": {
        "title": "Asset identity",
        "body": "Existing assets are addressed by GUID. Paths are contextual and are accepted only when selecting a new destination. Asset mutations use the editor's shared history and AssetDatabase.",
        "tags": ("asset", "guid", "path", "database"),
    },
    "validation": {
        "title": "Validation sessions",
        "body": "Synthetic input, semantic UI observation, render-target capture, and standalone Player validation require a Supervisor-owned global_validation session. Capture additionally requires debug_feedback.",
        "tags": ("validation", "supervisor", "capture", "input", "player"),
    },
    "authoring": {
        "title": "Authoring and Undo",
        "body": "Scene, component, material, particle, and asset commands enter authoritative editor services. Prefer GUID and object/component identities returned by queries instead of cached paths or display labels.",
        "tags": ("scene", "component", "material", "particle", "undo"),
    },
}


def build_docs_operations() -> tuple[Operation, ...]:
    return (
        operation(
            "infernux.docs.search",
            OperationKind.QUERY,
            "Search concise Infernux MCP guides and registered operation schemas.",
            _search,
            capability="docs.read",
            input_properties={
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            required=("query",),
            tags=("docs", "help", "search", "schema"),
        ),
        operation(
            "infernux.docs.read",
            OperationKind.QUERY,
            "Read one concise Infernux MCP guide by ID.",
            _read,
            capability="docs.read",
            input_properties={"guide": {"type": "string"}},
            required=("guide",),
            tags=("docs", "help", "guide"),
        ),
    )


def _search(query: str, limit: int = 20):
    terms = [part.casefold() for part in str(query).split() if part]
    guides = []
    for guide_id, guide in _GUIDES.items():
        haystack = " ".join((guide_id, guide["title"], guide["body"], *guide["tags"])).casefold()
        if all(term in haystack for term in terms):
            guides.append({"id": guide_id, "title": guide["title"], "tags": list(guide["tags"])})
    schemas = OperationRegistry.instance().search(query, limit=max(1, min(int(limit), 100)))
    return {
        "guides": guides[: max(1, min(int(limit), 100))],
        "operations": list(schemas),
    }


def _read(guide: str):
    guide_id = str(guide).strip().casefold()
    value = _GUIDES.get(guide_id)
    if value is None:
        raise OperationError("docs.not_found", f"Unknown guide: {guide}")
    return {"id": guide_id, "title": value["title"], "body": value["body"], "tags": list(value["tags"])}


__all__ = ["build_docs_operations"]
