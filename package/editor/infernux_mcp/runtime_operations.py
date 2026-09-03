"""Play Mode operations backed by the editor runtime state machine."""

from __future__ import annotations

import time

from Infernux.host import EditorAutomationHost, Operation, OperationError, OperationKind

from .operation_support import on_editor, operation


def build_runtime_operations() -> tuple[Operation, ...]:
    transition_input = {"timeout_seconds": {"type": "number", "default": 10.0}}
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
            lambda timeout_seconds=10.0: _transition(
                "infernux.runtime.play", "enter_play_mode", "playing", timeout_seconds
            ),
            capability="runtime.write",
            input_properties=transition_input,
            side_effects=("Replaces the edit world with a Play Mode world.",),
            tags=("runtime", "play-mode", "play"),
        ),
        operation(
            "infernux.runtime.stop",
            OperationKind.COMMAND,
            "Exit Play Mode through the editor state machine.",
            lambda timeout_seconds=10.0: _transition(
                "infernux.runtime.stop", "exit_play_mode", "edit", timeout_seconds
            ),
            capability="runtime.write",
            input_properties=transition_input,
            side_effects=("Stops Play Mode and restores the edit world.",),
            tags=("runtime", "play-mode", "stop"),
        ),
        operation(
            "infernux.runtime.pause",
            OperationKind.COMMAND,
            "Pause the active Play Mode world.",
            lambda timeout_seconds=10.0: _transition(
                "infernux.runtime.pause", "pause", "paused", timeout_seconds
            ),
            capability="runtime.write",
            input_properties=transition_input,
            side_effects=("Pauses Play Mode simulation.",),
            tags=("runtime", "play-mode", "pause"),
        ),
        operation(
            "infernux.runtime.resume",
            OperationKind.COMMAND,
            "Resume a paused Play Mode world.",
            lambda timeout_seconds=10.0: _transition(
                "infernux.runtime.resume", "resume", "playing", timeout_seconds
            ),
            capability="runtime.write",
            input_properties=transition_input,
            side_effects=("Resumes Play Mode simulation.",),
            tags=("runtime", "play-mode", "resume"),
        ),
        operation(
            "infernux.runtime.step",
            OperationKind.COMMAND,
            "Advance one frame while Play Mode is paused.",
            lambda: _transition(
                "infernux.runtime.step", "step_frame", "paused", 0.0,
                require_truthy=False,
            ),
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


def _transition(
    operation_id: str,
    method: str,
    expected_state: str,
    timeout_seconds: float,
    *,
    require_truthy: bool = True,
) -> dict[str, object]:
    def execute():
        result = EditorAutomationHost.instance().runtime_transition(method)
        if require_truthy and not result["accepted"]:
            raise OperationError("runtime.transition_rejected", f"Runtime transition was rejected: {method}")
        return result

    result = on_editor(operation_id, execute)
    timeout = max(0.0, min(float(timeout_seconds), 60.0))
    deadline = time.monotonic() + timeout
    runtime = dict(result.get("runtime") or {})
    while str(runtime.get("state", "")) != expected_state and time.monotonic() < deadline:
        time.sleep(0.02)
        runtime = on_editor(
            operation_id,
            lambda: EditorAutomationHost.instance().runtime_status(),
        )
    complete = str(runtime.get("state", "")) == expected_state
    if require_truthy and not complete:
        raise OperationError(
            "runtime.transition_timeout",
            f"Runtime did not reach {expected_state!r} within {timeout:.1f} seconds.",
            details={"runtime": runtime, "method": method},
        )
    return {
        "accepted": bool(result.get("accepted", True)),
        "transition_complete": complete,
        "target_state": expected_state,
        "runtime": runtime,
    }


def _set_time_scale(value: float) -> dict[str, object]:
    return on_editor(
        "infernux.runtime.time-scale.set",
        lambda: EditorAutomationHost.instance().set_time_scale(value),
    )


__all__ = ["build_runtime_operations"]
