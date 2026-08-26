"""Editor and game camera operations."""

from __future__ import annotations

from Infernux.host import Operation, OperationKind

from .operation_support import active_scene, on_editor, operation, plugin_manager


_VECTOR3 = {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}


def build_camera_operations() -> tuple[Operation, ...]:
    return (
        operation(
            "infernux.camera.editor.inspect",
            OperationKind.QUERY,
            "Read the editor Scene-view camera state.",
            _inspect_editor_camera,
            capability="camera.read",
            tags=("camera", "editor", "scene-view", "inspect"),
        ),
        operation(
            "infernux.camera.editor.state.set",
            OperationKind.COMMAND,
            "Restore the complete editor Scene-view camera state.",
            _set_editor_camera,
            capability="camera.write",
            input_properties={
                "position": _VECTOR3,
                "focus": _VECTOR3,
                "distance": {"type": "number"},
                "yaw": {"type": "number"},
                "pitch": {"type": "number"},
            },
            required=("position", "focus", "distance", "yaw", "pitch"),
            side_effects=("Moves the editor Scene-view camera.",),
            tags=("camera", "editor", "scene-view", "move"),
        ),
        operation(
            "infernux.camera.editor.focus",
            OperationKind.COMMAND,
            "Focus the editor camera on a world-space point.",
            _focus_editor_camera,
            capability="camera.write",
            input_properties={
                "point": _VECTOR3,
                "distance": {"type": "number", "default": 10.0},
            },
            required=("point",),
            side_effects=("Moves the editor Scene-view camera.",),
            tags=("camera", "editor", "focus", "scene-view"),
        ),
        operation(
            "infernux.camera.game.inspect",
            OperationKind.QUERY,
            "Read the effective game Camera component document.",
            _inspect_game_camera,
            capability="camera.read",
            tags=("camera", "game", "runtime", "inspect"),
        ),
    )


def _editor_camera():
    camera = getattr(getattr(plugin_manager(), "engine", None), "editor_camera", None)
    if camera is None:
        from Infernux.host import OperationError

        raise OperationError("editor.unavailable", "Editor camera is unavailable.")
    return camera


def _camera_state(camera) -> dict[str, object]:
    return {
        "position": list(camera.position),
        "rotation": list(camera.rotation),
        "focus": list(camera.focus_point),
        "distance": float(camera.focus_distance),
        "fov": float(camera.fov),
        "near_clip": float(camera.near_clip),
        "far_clip": float(camera.far_clip),
        "orthographic": bool(camera.orthographic),
        "orthographic_size": float(camera.orthographic_size),
    }


def _inspect_editor_camera() -> dict[str, object]:
    return on_editor(
        "infernux.camera.editor.inspect",
        lambda: {"camera": _camera_state(_editor_camera())},
    )


def _set_editor_camera(
    position: list[float],
    focus: list[float],
    distance: float,
    yaw: float,
    pitch: float,
) -> dict[str, object]:
    def edit():
        camera = _editor_camera()
        camera.restore_state(
            *[float(value) for value in position],
            *[float(value) for value in focus],
            float(distance),
            float(yaw),
            float(pitch),
        )
        return {"camera": _camera_state(camera)}

    return on_editor("infernux.camera.editor.state.set", edit)


def _focus_editor_camera(point: list[float], distance: float = 10.0) -> dict[str, object]:
    def edit():
        camera = _editor_camera()
        camera.focus_on(*[float(value) for value in point], float(distance))
        return {"camera": _camera_state(camera)}

    return on_editor("infernux.camera.editor.focus", edit)


def _inspect_game_camera() -> dict[str, object]:
    def read():
        camera = active_scene().effective_game_camera
        if camera is None:
            return {"camera": None}
        owner = getattr(camera, "game_object", None)
        serializer = getattr(camera, "serialize_document", None)
        return {
            "camera": {
                "object_id": int(getattr(owner, "id", 0) or 0),
                "component_id": int(getattr(camera, "component_id", 0) or 0),
                "document": serializer() if callable(serializer) else {},
            }
        }

    return on_editor("infernux.camera.game.inspect", read)


__all__ = ["build_camera_operations"]
