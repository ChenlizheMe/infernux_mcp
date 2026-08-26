"""Play Mode operations backed by the editor runtime state machine."""

from __future__ import annotations

from Infernux.host import EditorAutomationHost, Operation, OperationError, OperationKind

from .operation_support import on_editor, operation


def build_runtime_operations() -> tuple[Operation, ...]:
    return (
        operation(
            "infernux.runtime.status",
            OperationKind.QUERY,
            "Read Play Mode state, timing, pause state, and time scale.",
            _runtime_status,
            capability="runtime.read",
            tags=("runtime", "play-mode", "status", "time"),
        ),
        operation(
            "infernux.runtime.play",
            OperationKind.COMMAND,
            "Enter Play Mode through the editor state machine.",
            lambda: _transition("infernux.runtime.play", "enter_play_mode"),
            capability="runtime.write",
            side_effects=("Replaces the edit world with a Play Mode world.",),
            tags=("runtime", "play-mode", "play"),
        ),
        operation(
            "infernux.runtime.stop",
            OperationKind.COMMAND,
            "Exit Play Mode through the editor state machine.",
            lambda: _transition("infernux.runtime.stop", "exit_play_mode"),
            capability="runtime.write",
            side_effects=("Stops Play Mode and restores the edit world.",),
            tags=("runtime", "play-mode", "stop"),
        ),
        operation(
            "infernux.runtime.pause",
            OperationKind.COMMAND,
            "Pause the active Play Mode world.",
            lambda: _transition("infernux.runtime.pause", "pause"),
            capability="runtime.write",
            side_effects=("Pauses Play Mode simulation.",),
            tags=("runtime", "play-mode", "pause"),
        ),
        operation(
            "infernux.runtime.resume",
            OperationKind.COMMAND,
            "Resume a paused Play Mode world.",
            lambda: _transition("infernux.runtime.resume", "resume"),
            capability="runtime.write",
            side_effects=("Resumes Play Mode simulation.",),
            tags=("runtime", "play-mode", "resume"),
        ),
        operation(
            "infernux.runtime.step",
            OperationKind.COMMAND,
            "Advance one frame while Play Mode is paused.",
            lambda: _transition("infernux.runtime.step", "step_frame", require_truthy=False),
            capability="runtime.write",
            side_effects=("Advances the paused simulation by one frame.",),
            tags=("runtime", "play-mode", "step", "frame"),
        ),
        operation(
            "infernux.runtime.time-scale.set",
            OperationKind.COMMAND,
            "Set Play Mode time scale.",
            _set_time_scale,
            capability="runtime.write",
            input_properties={"value": {"type": "number"}},
            required=("value",),
            side_effects=("Changes the simulation time scale.",),
            tags=("runtime", "play-mode", "time", "scale"),
        ),
    )


def _runtime_status() -> dict[str, object]:
    return on_editor(
        "infernux.runtime.status",
        lambda: {"runtime": EditorAutomationHost.instance().runtime_status()},
    )


def _transition(operation_id: str, method: str, *, require_truthy: bool = True) -> dict[str, object]:
    def execute():
        result = EditorAutomationHost.instance().runtime_transition(method)
        if require_truthy and not result["accepted"]:
            raise OperationError("runtime.transition_rejected", f"Runtime transition was rejected: {method}")
        return result

    return on_editor(operation_id, execute)


def _set_time_scale(value: float) -> dict[str, object]:
    return on_editor(
        "infernux.runtime.time-scale.set",
        lambda: EditorAutomationHost.instance().set_time_scale(value),
    )


__all__ = ["build_runtime_operations"]
