"""Shared construction and editor-authority helpers for MCP operations."""

from __future__ import annotations

import copy
import os
from collections.abc import Callable, Mapping, MutableMapping, MutableSequence
from typing import Any

from Infernux.host import (
    EditorAutomationHost,
    MainThreadCommandQueue,
    Operation,
    OperationError,
    OperationKind,
    OperationSchema,
)


OWNER = "infernux/mcp"


def operation(
    operation_id: str,
    kind: OperationKind,
    summary: str,
    handler: Callable[..., Any],
    *,
    capability: str,
    input_properties: Mapping[str, object] | None = None,
    required: tuple[str, ...] = (),
    side_effects: tuple[str, ...] = (),
    reversible: bool = False,
    tags: tuple[str, ...] = (),
) -> Operation:
    schema = OperationSchema(
        id=operation_id,
        kind=kind,
        summary=summary,
        input_schema={
            "type": "object",
            "properties": dict(input_properties or {}),
            "required": list(required),
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        errors=(
            {"code": "operation.invalid_arguments"},
            {"code": "operation.permission_denied"},
            {"code": "operation.failed"},
            {"code": "editor.unavailable"},
            {"code": "asset.not_found"},
            {"code": "scene.object_not_found"},
        ),
        thread="mixed",
        side_effects=side_effects,
        reversible=bool(reversible),
        capabilities=(capability,),
        cost={"class": "interactive", "risk": "low" if not side_effects else "medium"},
        tags=tags,
    )
    return Operation(schema=schema, handler=handler, owner=OWNER)


def on_editor(operation_id: str, callback: Callable[[], Any]) -> Any:
    return MainThreadCommandQueue.instance().run_sync(
        operation_id,
        callback,
        timeout_ms=30000,
    )


def interaction_core():
    return EditorAutomationHost.instance().interaction_core()


def plugin_manager():
    return EditorAutomationHost.instance().plugin_manager()


def asset_database():
    return EditorAutomationHost.instance().asset_database()


def asset_path(asset_guid: str, *, suffix: str = "") -> str:
    guid = str(asset_guid or "").strip()
    if not guid:
        raise OperationError("operation.invalid_arguments", "asset_guid must not be empty")
    path = str(asset_database().get_path_from_guid(guid) or "")
    if not path or not os.path.exists(path):
        raise OperationError("asset.not_found", f"Asset GUID was not found: {guid}")
    if suffix and not path.casefold().endswith(suffix.casefold()):
        raise OperationError(
            "asset.type_mismatch",
            f"Asset {guid} is not a {suffix} resource.",
            details={"path": path},
        )
    return path


def asset_identity(path: str) -> dict[str, object]:
    database = asset_database()
    resolved = os.path.abspath(str(path))
    meta = database.get_meta_by_path(resolved)
    return {
        "guid": str(database.get_guid_from_path(resolved) or ""),
        "path": resolved,
        "name": os.path.basename(resolved),
        "is_directory": os.path.isdir(resolved),
        "resource_type": str(getattr(getattr(meta, "type", None), "name", "unknown")).lower(),
    }


def active_scene():
    return EditorAutomationHost.instance().active_scene()


def game_object(object_id: int):
    return EditorAutomationHost.instance().scene_object(int(object_id))


def components(object_id: int) -> list[Any]:
    return list(EditorAutomationHost.instance().scene_components(int(object_id)))


def component(object_id: int, component_id: int):
    obj = game_object(object_id)
    return obj, EditorAutomationHost.instance().scene_component(
        int(object_id), int(component_id)
    )


def serializable_component(value: Any) -> dict[str, object]:
    serializer = getattr(value, "serialize_document", None)
    if not callable(serializer):
        serializer = getattr(value, "_serialize_fields_document", None)
    try:
        document = serializer() if callable(serializer) else {}
    except Exception:
        document = {}
    result = {
        "component_id": int(getattr(value, "component_id", 0) or 0),
        "type": str(getattr(value, "type_name", "") or type(value).__name__),
        "enabled": bool(getattr(value, "enabled", True)),
        "document": document if isinstance(document, Mapping) else {},
    }
    script_guid = str(getattr(value, "_script_guid", "") or "")
    script_path = str(getattr(value, "_script_path", "") or "")
    type_guid_getter = getattr(type(value), "_get_type_guid", None)
    type_guid = str(type_guid_getter() or "") if callable(type_guid_getter) else ""
    if script_guid or script_path or type_guid:
        result["python"] = {
            "script_guid": script_guid,
            "type_guid": type_guid,
            "script_path": script_path,
            "type_name": f"{type(value).__module__}.{type(value).__qualname__}",
        }
    return result


def set_json_pointer(document: Mapping[str, Any], pointer: str, value: Any) -> dict[str, Any]:
    result = copy.deepcopy(dict(document))
    text = str(pointer or "").strip()
    if not text.startswith("/"):
        raise OperationError("operation.invalid_arguments", "JSON pointer must start with '/'.")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in text[1:].split("/")]
    current: Any = result
    for part in parts[:-1]:
        if isinstance(current, MutableMapping):
            if part not in current:
                raise OperationError("operation.invalid_arguments", f"JSON pointer does not exist: {text}")
            current = current[part]
        elif isinstance(current, MutableSequence):
            try:
                current = current[int(part)]
            except (IndexError, TypeError, ValueError) as exc:
                raise OperationError("operation.invalid_arguments", f"JSON pointer does not exist: {text}") from exc
        else:
            raise OperationError("operation.invalid_arguments", f"JSON pointer does not exist: {text}")
    leaf = parts[-1]
    if isinstance(current, MutableMapping):
        if leaf not in current:
            raise OperationError("operation.invalid_arguments", f"JSON pointer does not exist: {text}")
        current[leaf] = copy.deepcopy(value)
    elif isinstance(current, MutableSequence):
        try:
            current[int(leaf)] = copy.deepcopy(value)
        except (IndexError, TypeError, ValueError) as exc:
            raise OperationError("operation.invalid_arguments", f"JSON pointer does not exist: {text}") from exc
    else:
        raise OperationError("operation.invalid_arguments", f"JSON pointer does not exist: {text}")
    return result


__all__ = [
    "OWNER",
    "VERSION",
    "active_scene",
    "asset_database",
    "asset_identity",
    "asset_path",
    "component",
    "components",
    "game_object",
    "interaction_core",
    "on_editor",
    "operation",
    "plugin_manager",
    "serializable_component",
    "set_json_pointer",
]
