"""GUID-addressed project asset operations."""

from __future__ import annotations

import os

from Infernux.host import Operation, OperationError, OperationKind

from .operation_support import (
    asset_database,
    asset_identity,
    asset_path,
    interaction_core,
    on_editor,
    operation,
)


_CREATE_KINDS = {
    "folder": "",
    "script": ".py",
    "shader": ".glsl",
    "material": ".mat",
    "physic_material": ".physicMaterial",
    "scene": ".scene",
    "animation_clip": ".animclip2d",
    "animation_clip3d": ".animclip3d",
    "animation_fsm": ".animfsm",
    "particle_graph": ".particlegraph",
    "render_effect": ".effect",
    "render_effect_group": ".effectgroup",
    "animation_timeline": ".animtimeline",
    "timeline_fsm": ".timelinefsm",
}


def build_asset_operations() -> tuple[Operation, ...]:
    return (
        operation(
            "infernux.asset.list",
            OperationKind.QUERY,
            "List project assets with stable GUID identities.",
            _list_assets,
            capability="asset.read",
            input_properties={
                "query": {"type": "string", "default": ""},
                "extension": {"type": "string", "default": ""},
                "limit": {"type": "integer", "default": 200},
            },
            tags=("asset", "guid", "list", "search"),
        ),
        operation(
            "infernux.asset.inspect",
            OperationKind.QUERY,
            "Inspect one project asset addressed by GUID.",
            _inspect_asset,
            capability="asset.read",
            input_properties={"asset_guid": {"type": "string"}},
            required=("asset_guid",),
            tags=("asset", "guid", "inspect", "metadata"),
        ),
        operation(
            "infernux.asset.create.kinds",
            OperationKind.QUERY,
            "List asset kinds accepted by the project creation service.",
            lambda: {"kinds": [{"kind": key, "extension": value} for key, value in _CREATE_KINDS.items()]},
            capability="asset.read",
            tags=("asset", "create", "schema"),
        ),
        operation(
            "infernux.asset.create",
            OperationKind.COMMAND,
            "Create a project asset through the same transaction as the Project panel.",
            _create_asset,
            capability="asset.write",
            input_properties={
                "kind": {"type": "string"},
                "directory": {"type": "string"},
                "name": {"type": "string"},
                "variant": {"type": "string", "default": ""},
            },
            required=("kind", "directory", "name"),
            side_effects=("Creates and imports a project asset with Undo support.",),
            reversible=True,
            tags=("asset", "create", "import", "authoring"),
        ),
        operation(
            "infernux.asset.delete",
            OperationKind.COMMAND,
            "Delete project assets addressed by GUID through asset history.",
            _delete_assets,
            capability="asset.write",
            input_properties={"asset_guids": {"type": "array", "items": {"type": "string"}}},
            required=("asset_guids",),
            side_effects=("Deletes asset files and metadata with Undo support.",),
            reversible=True,
            tags=("asset", "guid", "delete", "authoring"),
        ),
        operation(
            "infernux.asset.move",
            OperationKind.COMMAND,
            "Move or rename one GUID-addressed asset inside the project.",
            _move_asset,
            capability="asset.write",
            input_properties={
                "asset_guid": {"type": "string"},
                "destination": {"type": "string"},
            },
            required=("asset_guid", "destination"),
            side_effects=("Moves an asset while preserving its GUID and records Undo.",),
            reversible=True,
            tags=("asset", "guid", "move", "rename", "authoring"),
        ),
        operation(
            "infernux.asset.refresh",
            OperationKind.COMMAND,
            "Refresh the authoritative AssetDatabase catalog.",
            _refresh_assets,
            capability="asset.write",
            side_effects=("Scans project asset roots and imports changed assets.",),
            tags=("asset", "database", "refresh", "import"),
        ),
    )


def _list_assets(query: str = "", extension: str = "", limit: int = 200) -> dict[str, object]:
    def read():
        database = asset_database()
        needle = str(query or "").casefold()
        suffix = str(extension or "").casefold()
        values = []
        for path in database.get_all_asset_paths():
            text = str(path)
            if needle and needle not in text.casefold():
                continue
            if suffix and not text.casefold().endswith(suffix):
                continue
            values.append(asset_identity(text))
            if len(values) >= max(1, min(int(limit), 2000)):
                break
        return {"assets": values, "returned": len(values), "catalog_count": int(database.asset_count)}

    return on_editor("infernux.asset.list", read)


def _inspect_asset(asset_guid: str) -> dict[str, object]:
    return on_editor(
        "infernux.asset.inspect",
        lambda: {"asset": asset_identity(asset_path(asset_guid))},
    )


def _create_asset(kind: str, directory: str, name: str, variant: str = "") -> dict[str, object]:
    def create():
        normalized = str(kind or "").strip()
        if normalized not in _CREATE_KINDS:
            raise OperationError("operation.invalid_arguments", f"Unknown asset kind: {kind}")
        core = interaction_core()
        service = core.project_asset_interactions
        if service.configured:
            path = service.create(
                normalized,
                directory,
                name,
                _CREATE_KINDS[normalized],
                variant,
            )
        else:
            # Headless owns the same command service but has no Project-panel
            # presentation callbacks. Keep creation non-visual while still
            # entering the authoritative asset Undo transaction.
            from Infernux.engine.ui import project_file_ops

            unique_name = project_file_ops.get_unique_name(
                directory,
                name,
                _CREATE_KINDS[normalized],
            )
            path = core.project_assets.create_with_path(
                directory,
                lambda: _create_headless_asset(
                    project_file_ops,
                    normalized,
                    directory,
                    unique_name,
                    variant,
                    core.project_assets.asset_database,
                ),
                description=f"Create {normalized.replace('_', ' ').title()}",
            )
        if not path:
            raise OperationError("asset.create_rejected", "Project asset creation was rejected.")
        return {"asset": asset_identity(path)}

    return on_editor("infernux.asset.create", create)


def _create_headless_asset(file_ops, kind: str, directory: str, name: str, variant: str, database):
    creators = {
        "folder": (file_ops.create_folder, (directory, name)),
        "script": (file_ops.create_script, (directory, name, database)),
        "shader": (file_ops.create_shader, (directory, name, variant, database)),
        "material": (file_ops.create_material, (directory, name, database)),
        "physic_material": (file_ops.create_physic_material, (directory, name, database)),
        "scene": (file_ops.create_scene, (directory, name, database)),
        "animation_clip": (file_ops.create_animclip, (directory, name, database)),
        "animation_clip3d": (file_ops.create_animclip3d, (directory, name, database)),
        "animation_fsm": (file_ops.create_animfsm, (directory, name, database)),
        "particle_graph": (file_ops.create_particlegraph, (directory, name, database)),
        "render_effect": (file_ops.create_render_effect, (directory, name, variant, database)),
        "render_effect_group": (file_ops.create_render_effect_group, (directory, name, database)),
        "animation_timeline": (file_ops.create_animtimeline, (directory, name, database)),
        "timeline_fsm": (file_ops.create_timelinefsm, (directory, name, database)),
    }
    callback, arguments = creators[kind]
    return callback(*arguments)


def _delete_assets(asset_guids: list[str]) -> dict[str, object]:
    def delete():
        paths = [asset_path(guid) for guid in asset_guids]
        deleted = interaction_core().project_assets.delete(paths)
        return {"deleted": [{"guid": guid, "path": path} for guid, path in zip(asset_guids, deleted)]}

    return on_editor("infernux.asset.delete", delete)


def _move_asset(asset_guid: str, destination: str) -> dict[str, object]:
    def move():
        source = asset_path(asset_guid)
        target = interaction_core().project_assets.move(source, destination)
        database = asset_database()
        resolved_guid = str(database.get_guid_from_path(target) or asset_guid)
        return {"asset": {**asset_identity(target), "guid": resolved_guid}}

    return on_editor("infernux.asset.move", move)


def _refresh_assets() -> dict[str, object]:
    def refresh():
        database = asset_database()
        database.refresh()
        return {
            "asset_count": int(database.asset_count),
            "imported": int(database.last_refresh_imported_count),
            "reused": int(database.last_refresh_reused_count),
            "scanned": int(database.last_refresh_scanned_count),
        }

    return on_editor("infernux.asset.refresh", refresh)


__all__ = ["build_asset_operations"]
