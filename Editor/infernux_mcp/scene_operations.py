"""Scene and component editing operations backed by editor transactions."""

from __future__ import annotations

from typing import Any

from Infernux.host import Operation, OperationError, OperationKind

from .operation_support import (
    active_scene,
    asset_path,
    component,
    game_object,
    interaction_core,
    on_editor,
    operation,
    serializable_component,
)


_VECTOR3 = {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}


def build_scene_operations() -> tuple[Operation, ...]:
    return (
        operation(
            "infernux.scene.hierarchy.get",
            OperationKind.QUERY,
            "Read the active scene hierarchy and serialized component state.",
            _hierarchy,
            capability="scene.read",
            tags=("scene", "hierarchy", "component", "inspect"),
        ),
        operation(
            "infernux.scene.object.kinds",
            OperationKind.QUERY,
            "List object kinds accepted by the editor's hierarchy creation service.",
            _object_kinds,
            capability="scene.read",
            tags=("scene", "object", "create", "schema"),
        ),
        operation(
            "infernux.scene.object.create",
            OperationKind.COMMAND,
            "Create one GameObject through hierarchy history.",
            _create_object,
            capability="scene.write",
            input_properties={
                "kind": {"type": "string"},
                "parent_id": {"type": "integer", "default": 0},
                "name": {"type": "string", "default": ""},
            },
            required=("kind",),
            side_effects=("Creates a scene object and records an Undo entry.",),
            reversible=True,
            tags=("scene", "object", "create", "authoring"),
        ),
        operation(
            "infernux.scene.object.delete",
            OperationKind.COMMAND,
            "Delete explicit GameObjects through one hierarchy transaction.",
            _delete_objects,
            capability="scene.write",
            input_properties={"object_ids": {"type": "array", "items": {"type": "integer"}}},
            required=("object_ids",),
            side_effects=("Deletes scene objects and records an Undo entry.",),
            reversible=True,
            tags=("scene", "object", "delete", "authoring"),
        ),
        operation(
            "infernux.scene.object.property.set",
            OperationKind.COMMAND,
            "Set one supported GameObject property through serialized-property history.",
            _set_object_property,
            capability="scene.write",
            input_properties={
                "object_id": {"type": "integer"},
                "property": {"type": "string", "enum": ["name", "active", "tag", "layer"]},
                "value": {},
            },
            required=("object_id", "property", "value"),
            side_effects=("Changes a GameObject property and records an Undo entry.",),
            reversible=True,
            tags=("scene", "object", "property", "authoring"),
        ),
        operation(
            "infernux.scene.object.transform.set",
            OperationKind.COMMAND,
            "Set the complete local transform of one GameObject.",
            _set_transform,
            capability="scene.write",
            input_properties={
                "object_id": {"type": "integer"},
                "position": _VECTOR3,
                "rotation": _VECTOR3,
                "scale": _VECTOR3,
            },
            required=("object_id", "position", "rotation", "scale"),
            side_effects=("Changes a Transform and records an Undo entry.",),
            reversible=True,
            tags=("scene", "object", "transform", "move", "authoring"),
        ),
        operation(
            "infernux.scene.object.parent.set",
            OperationKind.COMMAND,
            "Move GameObjects under a parent or to the scene root.",
            _set_parent,
            capability="scene.write",
            input_properties={
                "object_ids": {"type": "array", "items": {"type": "integer"}},
                "parent_id": {"type": "integer", "default": 0},
            },
            required=("object_ids",),
            side_effects=("Changes the hierarchy and records an Undo entry.",),
            reversible=True,
            tags=("scene", "hierarchy", "parent", "move", "authoring"),
        ),
        operation(
            "infernux.scene.component.add",
            OperationKind.COMMAND,
            "Attach a registered native or Python component to a GameObject.",
            _add_component,
            capability="scene.write",
            input_properties={
                "object_id": {"type": "integer"},
                "component_type": {"type": "string"},
            },
            required=("object_id", "component_type"),
            side_effects=("Attaches a component and records an Undo entry.",),
            reversible=True,
            tags=("scene", "component", "add", "authoring"),
        ),
        operation(
            "infernux.scene.component.property.set",
            OperationKind.COMMAND,
            "Set one serialized component field through the shared component service.",
            _set_component_property,
            capability="scene.write",
            input_properties={
                "object_id": {"type": "integer"},
                "component_id": {"type": "integer"},
                "field": {"type": "string"},
                "value": {},
            },
            required=("object_id", "component_id", "field", "value"),
            side_effects=("Changes a component field and records an Undo entry.",),
            reversible=True,
            tags=("scene", "component", "property", "authoring"),
        ),
        operation(
            "infernux.scene.open",
            OperationKind.COMMAND,
            "Open a scene asset addressed by GUID.",
            _open_scene,
            capability="scene.write",
            input_properties={"asset_guid": {"type": "string"}},
            required=("asset_guid",),
            side_effects=("Replaces the active scene document.",),
            tags=("scene", "document", "open", "asset"),
        ),
        operation(
            "infernux.scene.save",
            OperationKind.COMMAND,
            "Save the active scene through its registered document controller.",
            _save_scene,
            capability="scene.write",
            side_effects=("Durably writes the active scene asset.",),
            tags=("scene", "document", "save"),
        ),
    )


def _hierarchy() -> dict[str, object]:
    def read() -> dict[str, object]:
        scene = active_scene()

        def serialize(obj) -> dict[str, object]:
            transform = obj.get_transform()
            values = list(obj.get_components()) + list(obj.get_py_components())
            return {
                "id": int(obj.id),
                "name": str(obj.name),
                "active": bool(getattr(obj, "active", True)),
                "tag": str(getattr(obj, "tag", "")),
                "layer": int(getattr(obj, "layer", 0)),
                "transform": {
                    "position": list(transform.local_position),
                    "rotation": list(transform.local_euler_angles),
                    "scale": list(transform.local_scale),
                },
                "components": [serializable_component(value) for value in values],
                "children": [serialize(child) for child in obj.get_children()],
            }

        return {
            "name": str(scene.name),
            "structure_version": int(getattr(scene, "structure_version", 0)),
            "objects": [serialize(obj) for obj in scene.get_root_objects()],
        }

    return on_editor("infernux.scene.hierarchy.get", read)


def _object_kinds() -> dict[str, object]:
    def read():
        from Infernux.engine.hierarchy_creation_service import HierarchyCreationService

        return {"kinds": HierarchyCreationService.instance().list_create_kinds()}

    return on_editor("infernux.scene.object.kinds", read)


def _create_object(kind: str, parent_id: int = 0, name: str = "") -> dict[str, object]:
    def create():
        from Infernux.engine.hierarchy_creation_service import HierarchyCreationService

        service = HierarchyCreationService.instance()
        if not service.can_create(kind, parent_id=int(parent_id)):
            raise OperationError("scene.create_rejected", f"Cannot create object kind {kind!r}.")
        return service.create(
            kind,
            parent_id=int(parent_id),
            name=str(name or "") or None,
            select=False,
            selection_owner_id="automation",
            selection_reason="mcp_create_game_object",
        )

    return on_editor("infernux.scene.object.create", create)


def _delete_objects(object_ids: list[int]) -> dict[str, object]:
    def delete():
        ids = [int(value) for value in object_ids]
        changed = interaction_core().scene_objects.delete_ids(ids, selection_owner_id="automation")
        if not changed:
            raise OperationError("scene.edit_rejected", "No GameObjects were deleted.")
        return {"deleted": ids}

    return on_editor("infernux.scene.object.delete", delete)


def _set_object_property(object_id: int, property: str, value: Any) -> dict[str, object]:
    def edit():
        changed = interaction_core().scene_objects.set_object_property(object_id, property, value)
        if not changed:
            raise OperationError("scene.edit_rejected", "GameObject property edit was rejected or unchanged.")
        return {"object_id": int(object_id), "property": property, "value": value}

    return on_editor("infernux.scene.object.property.set", edit)


def _set_transform(
    object_id: int,
    position: list[float],
    rotation: list[float],
    scale: list[float],
) -> dict[str, object]:
    values = {"position": position, "rotation": rotation, "scale": scale}

    def edit():
        changed = interaction_core().scene_objects.set_transforms([object_id], [values])
        if not changed:
            raise OperationError("scene.edit_rejected", "Transform edit was rejected or unchanged.")
        return {"object_id": int(object_id), "transform": values}

    return on_editor("infernux.scene.object.transform.set", edit)


def _set_parent(object_ids: list[int], parent_id: int = 0) -> dict[str, object]:
    def edit():
        mode = "parent" if int(parent_id) else "root"
        changed = interaction_core().scene_objects.move_hierarchy(object_ids, mode, int(parent_id))
        if not changed:
            raise OperationError("scene.edit_rejected", "Hierarchy edit was rejected or unchanged.")
        return {"object_ids": [int(value) for value in object_ids], "parent_id": int(parent_id)}

    return on_editor("infernux.scene.object.parent.set", edit)


def _add_component(object_id: int, component_type: str) -> dict[str, object]:
    def edit():
        value = interaction_core().components.add(game_object(object_id), component_type)
        return {"object_id": int(object_id), "component": serializable_component(value)}

    return on_editor("infernux.scene.component.add", edit)


def _set_component_property(
    object_id: int,
    component_id: int,
    field: str,
    value: Any,
) -> dict[str, object]:
    def edit():
        _, target = component(object_id, component_id)
        changed = interaction_core().components.set_field(target, field, value)
        if not changed:
            raise OperationError("scene.edit_rejected", "Component field edit was rejected or unchanged.")
        return {"object_id": int(object_id), "component": serializable_component(target)}

    return on_editor("infernux.scene.component.property.set", edit)


def _open_scene(asset_guid: str) -> dict[str, object]:
    def open_document():
        from Infernux.engine.scene_manager import SceneFileManager

        path = asset_path(asset_guid, suffix=".scene")
        manager = SceneFileManager.instance()
        if manager is None or not manager.open_scene(path):
            raise OperationError("scene.open_rejected", "The scene could not be opened.")
        return {"asset_guid": asset_guid, "path": path, "opened": True}

    return on_editor("infernux.scene.open", open_document)


def _save_scene() -> dict[str, object]:
    def save():
        from Infernux.engine.scene_manager import SceneFileManager

        manager = SceneFileManager.instance()
        if manager is None or not manager.save_current_scene():
            raise OperationError("scene.save_rejected", "The active scene could not be saved synchronously.")
        return {"saved": True, "path": str(manager.current_scene_path or "")}

    return on_editor("infernux.scene.save", save)


__all__ = ["build_scene_operations"]
