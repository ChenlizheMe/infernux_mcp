"""Material document and renderer-slot operations."""

from __future__ import annotations

from Infernux.host import EditorAutomationHost, Operation, OperationError, OperationKind

from .operation_support import (
    asset_path,
    component,
    interaction_core,
    on_editor,
    operation,
    set_json_pointer,
)


def build_material_operations() -> tuple[Operation, ...]:
    return (
        operation(
            "infernux.material.inspect",
            OperationKind.QUERY,
            "Read one material's canonical document by asset GUID.",
            _inspect_material,
            capability="material.read",
            input_properties={"asset_guid": {"type": "string"}},
            required=("asset_guid",),
            tags=("material", "asset", "guid", "inspect"),
        ),
        operation(
            "infernux.material.property.set",
            OperationKind.COMMAND,
            "Set an existing value in a material document using a JSON pointer.",
            _set_material_property,
            capability="material.write",
            input_properties={
                "asset_guid": {"type": "string"},
                "pointer": {"type": "string"},
                "value": {},
            },
            required=("asset_guid", "pointer", "value"),
            side_effects=("Changes and durably saves a material through editor history.",),
            reversible=True,
            tags=("material", "asset", "guid", "property", "authoring"),
        ),
        operation(
            "infernux.material.slot.assign",
            OperationKind.COMMAND,
            "Assign a GUID-addressed material to a renderer slot.",
            _assign_material_slot,
            capability="material.write",
            input_properties={
                "object_id": {"type": "integer"},
                "component_id": {"type": "integer"},
                "slot": {"type": "integer", "default": 0},
                "material_guid": {"type": "string"},
            },
            required=("object_id", "component_id", "material_guid"),
            side_effects=("Changes a renderer material slot and records an Undo entry.",),
            reversible=True,
            tags=("material", "renderer", "slot", "scene", "authoring"),
        ),
    )


def _load_material(asset_guid: str):
    path = asset_path(asset_guid, suffix=".mat")
    material, document = EditorAutomationHost.instance().material_document(path)
    return path, material, document


def _inspect_material(asset_guid: str) -> dict[str, object]:
    def read():
        path, _material, document = _load_material(asset_guid)
        return {"asset_guid": asset_guid, "path": path, "document": document}

    return on_editor("infernux.material.inspect", read)


def _set_material_property(asset_guid: str, pointer: str, value) -> dict[str, object]:
    def edit():
        path, _material, before = _load_material(asset_guid)
        after = set_json_pointer(before, pointer, value)
        EditorAutomationHost.instance().publish_material_document(
            path,
            asset_guid,
            after,
            edit_key=f"material:{pointer}",
            description=f"Set Material {pointer}",
        )
        return {"asset_guid": asset_guid, "path": path, "pointer": pointer, "document": after}

    return on_editor("infernux.material.property.set", edit)


def _assign_material_slot(
    object_id: int,
    component_id: int,
    material_guid: str,
    slot: int = 0,
) -> dict[str, object]:
    def edit():
        asset_path(material_guid, suffix=".mat")
        _, renderer = component(object_id, component_id)
        getter = getattr(renderer, "get_material_guids", None)
        if not callable(getter):
            raise OperationError("material.renderer_required", "Target component has no material slots.")
        values = list(getter())
        index = int(slot)
        if index < 0:
            raise OperationError("operation.invalid_arguments", "slot must be non-negative")
        old_guid = str(values[index] or "") if index < len(values) else ""
        changed = interaction_core().components.set_material_slot(
            renderer,
            index,
            old_guid,
            material_guid,
        )
        if not changed:
            raise OperationError("material.edit_rejected", "Material slot edit was rejected or unchanged.")
        return {
            "object_id": int(object_id),
            "component_id": int(component_id),
            "slot": index,
            "material_guid": material_guid,
        }

    return on_editor("infernux.material.slot.assign", edit)


__all__ = ["build_material_operations"]
