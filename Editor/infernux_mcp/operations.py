"""Native OperationSchema implementations owned by the MCP plugin."""

from __future__ import annotations

from collections.abc import Callable

from Infernux.host import (
    Operation,
    OperationError,
    OperationKind,
)

from infernux_mcp import session
from infernux_mcp.asset_operations import build_asset_operations
from infernux_mcp.camera_operations import build_camera_operations
from infernux_mcp.material_operations import build_material_operations
from infernux_mcp.operation_support import OWNER, on_editor, operation
from infernux_mcp.particle_operations import build_particle_operations
from infernux_mcp.runtime_operations import build_runtime_operations
from infernux_mcp.scene_operations import build_scene_operations


def build_operations(project_path: str) -> tuple[Operation, ...]:
    """Build the explicit operation surface for this plugin lifetime."""

    session_operations = (
        operation(
            "infernux.project.info",
            OperationKind.QUERY,
            "Read the active project, scene document, and play state.",
            _project_info_handler(project_path),
            capability="project.read",
            tags=("project", "scene", "status"),
        ),
        operation(
            "infernux.mcp.checkpoint.list",
            OperationKind.QUERY,
            "List payload-verified Supervisor checkpoints for this session.",
            lambda: {"checkpoints": session.list_checkpoints()},
            capability="session.read",
            tags=("session", "checkpoint"),
        ),
        operation(
            "infernux.mcp.checkpoint.status",
            OperationKind.QUERY,
            "Verify one Supervisor checkpoint against the current project ledger.",
            lambda checkpoint: session.checkpoint_status(checkpoint),
            capability="session.read",
            input_properties={"checkpoint": {"type": "string"}},
            required=("checkpoint",),
            tags=("session", "checkpoint", "verification"),
        ),
        operation(
            "infernux.mcp.supervisor.shutdown",
            OperationKind.COMMAND,
            "Request normal Editor shutdown using the private Supervisor lease.",
            _supervisor_shutdown,
            capability="session.write",
            input_properties={"lease_token": {"type": "string"}},
            required=("lease_token",),
            side_effects=("Requests the Editor's normal close lifecycle.",),
            tags=("session", "supervisor", "shutdown"),
        ),
        operation(
            "infernux.mcp.attempt.start",
            OperationKind.COMMAND,
            "Start a checkpoint-bound validation attempt and trace.",
            lambda task, checkpoint="": session.start_attempt(task, checkpoint),
            capability="session.write",
            input_properties={
                "task": {"type": "string"},
                "checkpoint": {"type": "string", "default": ""},
            },
            required=("task",),
            side_effects=("Starts a validation trace for the active project.",),
            tags=("session", "attempt", "trace"),
        ),
        operation(
            "infernux.mcp.attempt.stop",
            OperationKind.COMMAND,
            "Stop and save the active validation attempt trace.",
            session.stop_attempt,
            capability="session.write",
            side_effects=("Writes the active trace into the session artifact directory.",),
            tags=("session", "attempt", "trace"),
        ),
        operation(
            "infernux.mcp.blocker.report",
            OperationKind.COMMAND,
            "Persist a trace-backed validation blocker report.",
            lambda report: session.write_blocker(report),
            capability="session.write",
            input_properties={"report": {"type": "object"}},
            required=("report",),
            side_effects=("Writes a blocker report into the session artifact directory.",),
            tags=("session", "validation", "blocker", "report"),
        ),
    )
    return (
        session_operations
        + build_scene_operations()
        + build_asset_operations()
        + build_material_operations()
        + build_particle_operations()
        + build_camera_operations()
        + build_runtime_operations()
    )


def _project_info_handler(project_path: str) -> Callable[[], dict[str, object]]:
    def execute() -> dict[str, object]:
        def read() -> dict[str, object]:
            from Infernux.engine.play_mode import PlayModeManager
            from Infernux.engine.scene_manager import SceneFileManager
            from Infernux.lib import SceneManager

            scene_files = SceneFileManager.instance()
            play_mode = PlayModeManager.instance()
            scene = SceneManager.instance().get_active_scene()
            return {
                "project_root": project_path,
                "active_scene": {
                    "name": str(getattr(scene, "name", "")),
                    "path": str(getattr(scene_files, "current_scene_path", ""))
                    if scene_files
                    else "",
                    "dirty": bool(getattr(scene_files, "is_dirty", False))
                    if scene_files
                    else False,
                },
                "play_state": str(
                    getattr(getattr(play_mode, "state", None), "name", "edit")
                ).lower(),
            }

        return on_editor("infernux.project.info", read)

    return execute


def _supervisor_shutdown(lease_token: str) -> dict[str, object]:
    try:
        active = session.require_supervisor_lease(lease_token)
    except session.McpPolicyError as exc:
        raise OperationError("mcp.supervisor_lease", str(exc)) from exc

    def request_close() -> dict[str, object]:
        from Infernux.engine.scene_manager import SceneFileManager

        manager = SceneFileManager.instance()
        if manager is None:
            raise OperationError(
                "mcp.editor_unavailable",
                "SceneFileManager is unavailable for normal Editor shutdown.",
            )
        manager.request_close()
        return {
            "close_requested": True,
            "editor_instance_id": active.editor_instance_id,
        }

    return on_editor("infernux.mcp.supervisor.shutdown", request_close)


__all__ = ["OWNER", "build_operations"]
