"""OperationSchema v0 adapter and the small default MCP gateway surface."""

from __future__ import annotations

import inspect
import json
import re
import threading
import time
import types
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Union, get_args, get_origin, get_type_hints

from Infernux.host import (
    Operation,
    OperationError,
    OperationJobRegistry,
    OperationKind,
    OperationRegistry,
    OperationSchema,
)


OWNER = "infernux/mcp"
GATEWAY_VERSION = 0
MAX_GATEWAY_TOOLS = 32

_registry: OperationRegistry | None = None
_jobs: OperationJobRegistry | None = None
_tool_to_operation: dict[str, str] = {}
_gateway_names: set[str] = set()
_state_lock = threading.RLock()
_started_at = 0.0
_registration_ms = 0.0
_full_schema_bytes = 0
_compact_schema_bytes = 0
_config: dict[str, Any] = {}


@dataclass(slots=True)
class _CapturedTool:
    name: str
    handler: Callable[..., Any]


class _OperationCollector:
    """FastMCP-shaped collector that never exposes the captured flat tools."""

    def __init__(self) -> None:
        self.tools: dict[str, _CapturedTool] = {}

    def tool(self, *args, **kwargs):
        explicit_name = kwargs.get("name")
        if explicit_name is None and args and isinstance(args[0], str):
            explicit_name = args[0]

        def decorate(fn):
            name = str(explicit_name or getattr(fn, "__name__", "")).strip()
            if not name:
                raise ValueError("Captured MCP tool has no stable name")
            if name in self.tools:
                raise ValueError(f"Duplicate captured MCP tool: {name}")
            self.tools[name] = _CapturedTool(name, fn)
            return fn

        return decorate


def register_gateways(
    mcp,
    project_path: str,
    config: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Register legacy capabilities as operations and expose <=32 gateways."""

    global _registry, _jobs, _started_at, _config
    global _registration_ms, _full_schema_bytes, _compact_schema_bytes
    with _state_lock:
        registration_started = time.perf_counter()
        shutdown_adapter()
        _config = dict(config or {})
        registry = OperationRegistry.instance()
        registry.unregister_owner(OWNER)
        collector = _OperationCollector()
        from infernux_mcp import capabilities
        if config is None:
            _config = capabilities.configure(project_path, write_default=False)
        else:
            _config = capabilities.apply_config(project_path, dict(config))
        from infernux_mcp import session
        # Registration defines a new adapter lifetime and therefore a new
        # project/policy session.  Reusing a process-global session from a
        # previous project changes which operations are captured (for example
        # developer-assist authoring operations) and makes startup order-dependent.
        session.configure(project_path, dict(_config))
        from infernux_mcp.tools import register_all_tools

        register_all_tools(collector, project_path, dict(_config))
        _tool_to_operation.clear()
        for captured in sorted(collector.tools.values(), key=lambda item: item.name):
            operation = _captured_operation(captured)
            registry.register(operation)
            _tool_to_operation[captured.name] = operation.schema.id
        _registry = registry
        _jobs = OperationJobRegistry(registry)
        _started_at = time.time()
        documents = registry.list()
        _full_schema_bytes = len(
            json.dumps(
                documents,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        _compact_schema_bytes = len(
            json.dumps(
                [_compact_schema(value) for value in documents],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        _register_gateway_tools(mcp, project_path)
        if len(_gateway_names) > MAX_GATEWAY_TOOLS:
            raise RuntimeError(
                f"Default MCP gateway exceeds {MAX_GATEWAY_TOOLS} tools: "
                f"{len(_gateway_names)}"
            )
        _registration_ms = (time.perf_counter() - registration_started) * 1000.0
        return adapter_status()


def shutdown_adapter() -> None:
    global _registry, _jobs, _started_at
    global _registration_ms, _full_schema_bytes, _compact_schema_bytes
    with _state_lock:
        if _jobs is not None:
            remaining = _jobs.shutdown(
                wait=True, cancel_futures=True, timeout=5.0
            )
            if remaining:
                raise RuntimeError(
                    f"{remaining} MCP operation job(s) did not stop within 5 seconds"
                )
        _jobs = None
        if _registry is not None:
            _registry.unregister_owner(OWNER)
        _registry = None
        _tool_to_operation.clear()
        _gateway_names.clear()
        _started_at = 0.0
        _registration_ms = 0.0
        _full_schema_bytes = 0
        _compact_schema_bytes = 0


def adapter_status() -> dict[str, object]:
    registry = _registry
    return {
        "owner": OWNER,
        "schema_version": GATEWAY_VERSION,
        "active": registry is not None,
        "revision": 0 if registry is None else registry.revision,
        "operation_count": len(_tool_to_operation),
        "gateway_count": len(_gateway_names),
        "gateway_tools": sorted(_gateway_names),
        "started_at": _started_at,
        "registration_ms": _registration_ms,
        "full_schema_bytes": _full_schema_bytes,
        "compact_schema_bytes": _compact_schema_bytes,
    }


def operation_id_for_tool(tool_name: str) -> str:
    value = _tool_to_operation.get(str(tool_name))
    if value:
        return value
    candidate = _operation_id(str(tool_name))
    if _registry is not None:
        _registry.get(candidate)
    return candidate


def _register_gateway_tools(mcp, project_path: str) -> None:
    _gateway_names.clear()

    def gateway(name: str):
        _gateway_names.add(name)
        return mcp.tool(name=name)

    @gateway("mcp_ping")
    def mcp_ping() -> dict[str, object]:
        """Return transport and operation-registry readiness."""

        return _ok({"message": "pong", **adapter_status()})

    @gateway("operation_schema_list")
    def operation_schema_list(
        kind: str = "", capability: str = "", offset: int = 0, limit: int = 50
    ) -> dict[str, object]:
        """List compact OperationSchema records with deterministic pagination."""

        try:
            values = _require_registry().list(kind=kind or None, capability=capability)
            start = max(int(offset), 0)
            stop = start + min(max(int(limit), 1), 200)
            return _ok(
                {
                    "revision": _require_registry().revision,
                    "total": len(values),
                    "offset": start,
                    "operations": [_compact_schema(value) for value in values[start:stop]],
                }
            )
        except (ValueError, OperationError) as exc:
            return _error(exc)

    @gateway("operation_schema_get")
    def operation_schema_get(operation: str) -> dict[str, object]:
        """Return one complete OperationSchema v0 document."""

        try:
            return _ok(_require_registry().get(_resolve_operation(operation)).schema.document())
        except OperationError as exc:
            return _error(exc)

    @gateway("operation_schema_search")
    def operation_schema_search(query: str, limit: int = 50) -> dict[str, object]:
        """Search operation IDs, summaries and domain tags."""

        try:
            values = _require_registry().search(query, limit=min(max(int(limit), 1), 200))
            return _ok(
                {
                    "revision": _require_registry().revision,
                    "operations": [_compact_schema(value) for value in values],
                }
            )
        except OperationError as exc:
            return _error(exc)

    @gateway("operation_query_execute")
    def operation_query_execute(
        operation: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, object]:
        """Execute one query operation after schema and capability validation."""

        return _execute(operation, arguments, expected_kind=OperationKind.QUERY)

    @gateway("operation_command_execute")
    def operation_command_execute(
        operation: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, object]:
        """Execute one command operation after schema and capability validation."""

        return _execute(operation, arguments, expected_kind=OperationKind.COMMAND)

    @gateway("operation_workflow_invoke")
    def operation_workflow_invoke(
        operation: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, object]:
        """Invoke one compound workflow operation."""

        return _execute(operation, arguments, expected_kind=OperationKind.WORKFLOW)

    @gateway("operation_execute")
    def operation_execute(
        operation: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, object]:
        """Execute an operation when its kind is already known from discovery."""

        return _execute(operation, arguments)

    @gateway("operation_batch_execute")
    def operation_batch_execute(
        calls: list[dict[str, Any]], stop_on_error: bool = True
    ) -> dict[str, object]:
        """Execute a bounded ordered batch of schema operations."""

        try:
            maximum = int((_config.get("limits") or {}).get("batch_max_steps", 100))
            if len(calls) > maximum:
                raise OperationError(
                    "operation.batch_too_large", f"Batch exceeds {maximum} calls"
                )
            normalized = [
                {
                    **dict(call),
                    "operation": _resolve_operation(str(call.get("operation", ""))),
                }
                for call in calls
            ]
            return _ok(
                {
                    "results": list(
                        _require_registry().execute_batch(
                            normalized,
                            capabilities=_granted_capabilities(),
                            stop_on_error=bool(stop_on_error),
                        )
                    )
                }
            )
        except OperationError as exc:
            return _error(exc)

    @gateway("operation_job_submit")
    def operation_job_submit(
        operation: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, object]:
        """Submit a potentially long operation to the bounded Host job pool."""

        try:
            job_id = _require_jobs().submit(
                _resolve_operation(operation),
                arguments,
                capabilities=_granted_capabilities(),
            )
            return _ok({"job_id": job_id})
        except OperationError as exc:
            return _error(exc)

    @gateway("operation_job_status")
    def operation_job_status(job_id: str) -> dict[str, object]:
        """Inspect one asynchronous operation job."""

        try:
            return _ok(_require_jobs().status(job_id))
        except OperationError as exc:
            return _error(exc)

    @gateway("operation_job_cancel")
    def operation_job_cancel(job_id: str) -> dict[str, object]:
        """Cancel a queued operation job when it has not begun execution."""

        try:
            return _ok({"job_id": job_id, "cancelled": _require_jobs().cancel(job_id)})
        except OperationError as exc:
            return _error(exc)

    @gateway("host_capabilities")
    def host_capabilities() -> dict[str, object]:
        """Describe granted capabilities and active schema revision."""

        return _ok(
            {
                "granted": list(_granted_capabilities()),
                "operation_revision": _require_registry().revision,
                "operation_count": len(_tool_to_operation),
                "gateway_count": len(_gateway_names),
            }
        )

    @gateway("host_session_status")
    def host_session_status() -> dict[str, object]:
        """Return project/session state without advertising session internals."""

        try:
            from infernux_mcp import session

            state = session.current_state()
            value = state.to_dict() if hasattr(state, "to_dict") else vars(state)
        except Exception as exc:
            value = {"project_path": project_path, "error": f"{type(exc).__name__}: {exc}"}
        return _ok({"session": value, **adapter_status()})


def _captured_operation(captured: _CapturedTool) -> Operation:
    from infernux_mcp.tools.common import get_tool_metadata

    metadata = get_tool_metadata(captured.name)
    kind = _operation_kind(captured.name, metadata)
    domain = _domain(captured.name, metadata)
    side_effects = tuple(str(item) for item in metadata.get("side_effects", []) if str(item))
    required_capability = f"{domain}.{'read' if kind == OperationKind.QUERY else 'write'}"
    schema = OperationSchema(
        id=_operation_id(captured.name),
        version=GATEWAY_VERSION,
        kind=kind,
        summary=str(metadata.get("summary") or inspect.getdoc(captured.handler) or captured.name),
        input_schema=_input_schema(captured.handler, metadata),
        output_schema={
            "type": "object",
            "description": "Structured legacy operation result envelope.",
        },
        errors=(
            {"code": "operation.invalid_arguments"},
            {"code": "operation.permission_denied"},
            {"code": "operation.rejected"},
            {"code": "operation.failed"},
        ),
        thread="mixed",
        side_effects=side_effects,
        reversible=any("undo" in item.casefold() for item in side_effects),
        capabilities=(required_capability,),
        cost={
            "class": "interactive",
            "risk": str(metadata.get("risk_level", "medium")),
        },
        tags=tuple(
            dict.fromkeys(
                [captured.name, domain, str(metadata.get("category", "")), *metadata.get("tags", [])]
            )
        ),
    )
    return Operation(schema, _operation_handler(captured), OWNER)


def _operation_handler(captured: _CapturedTool) -> Callable[..., Any]:
    """Translate legacy result envelopes into transport-neutral failures."""

    def execute(**arguments):
        result = captured.handler(**arguments)
        if isinstance(result, Mapping) and result.get("ok") is False:
            raw_error = result.get("error")
            error = dict(raw_error) if isinstance(raw_error, Mapping) else {}
            message = str(error.get("message") or f"{captured.name} was rejected")
            raise OperationError(
                "operation.rejected",
                message,
                details={
                    "tool": captured.name,
                    "legacy_error": error,
                    "recovery": result.get("explain"),
                    "data": result.get("data"),
                },
            )
        return result

    return execute


def _operation_id(tool_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", str(tool_name).casefold()).strip("_")
    return "infernux." + normalized.replace("_", ".")


def _operation_kind(name: str, metadata: Mapping[str, Any]) -> OperationKind:
    lowered = str(name).casefold()
    if lowered.startswith("workflow_") or any(
        marker in lowered for marker in ("_batch_", "_setup_", "_validate_game")
    ):
        return OperationKind.WORKFLOW
    mutation_words = {
        "add", "apply", "build", "cancel", "clear", "copy", "create", "delete",
        "discard", "duplicate", "edit", "emit", "ensure", "import", "inject",
        "install", "invoke", "move", "new", "open", "patch", "pause", "reload",
        "remove", "rename", "request", "restart", "save", "select", "send", "set",
        "start", "stop", "terminate", "uninstall", "update", "write",
    }
    words = set(lowered.replace(".", "_").split("_"))
    side_effects = [str(item).casefold() for item in metadata.get("side_effects", [])]
    if words & mutation_words or any(
        item and not item.startswith(("no ", "none")) for item in side_effects
    ):
        return OperationKind.COMMAND
    return OperationKind.QUERY


def _domain(name: str, metadata: Mapping[str, Any]) -> str:
    category = str(metadata.get("category", "")).split("/", 1)[0].strip()
    if category and category not in {"misc", "foundation"}:
        return re.sub(r"[^a-z0-9]+", "_", category.casefold()).strip("_")
    return re.sub(r"[^a-z0-9]+", "_", str(name).split("_", 1)[0].casefold()) or "engine"


def _input_schema(handler: Callable[..., Any], metadata: Mapping[str, Any]) -> dict[str, object]:
    properties: dict[str, object] = {}
    required: list[str] = []
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        signature = None
    try:
        resolved_hints = get_type_hints(handler)
    except (NameError, TypeError):
        resolved_hints = {}
    if signature is not None:
        for name, parameter in signature.parameters.items():
            if name.startswith("_"):
                continue
            value: dict[str, object] = {}
            json_type = _annotation_json_type(
                resolved_hints.get(name, parameter.annotation)
            )
            if json_type is not None:
                value["type"] = json_type
            if parameter.default is inspect.Parameter.empty:
                required.append(name)
            elif parameter.default is None or isinstance(
                parameter.default, (bool, int, float, str, list, dict)
            ):
                value["default"] = parameter.default
            properties[name] = value
    descriptions = metadata.get("parameters", {})
    if isinstance(descriptions, Mapping):
        for name, description in descriptions.items():
            if name in properties and isinstance(description, Mapping):
                text = description.get("description")
                if text:
                    properties[name]["description"] = str(text)  # type: ignore[index]
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _annotation_json_type(annotation: object) -> str | list[str] | None:
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        members: list[str] = []
        for item in get_args(annotation):
            if item is type(None):
                continue
            mapped = _annotation_json_type(item)
            candidates = mapped if isinstance(mapped, list) else [mapped]
            for candidate in candidates:
                if candidate is not None and candidate not in members:
                    members.append(candidate)
        if len(members) == 1:
            return members[0]
        return members or None
    if origin in (list, tuple, set, frozenset):
        return "array"
    if origin in (dict, Mapping):
        return "object"
    if annotation is bool:
        return "boolean"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is str:
        return "string"

    text = str(annotation).casefold()
    # Container syntax includes its element type (for example list[float]);
    # classify the outer shape before inspecting scalar tokens.
    if "list" in text or "tuple" in text or "sequence" in text:
        return "array"
    if "dict" in text or "mapping" in text:
        return "object"
    scalar_members = [
        json_type
        for token, json_type in (
            ("bool", "boolean"),
            ("int", "integer"),
            ("float", "number"),
            ("str", "string"),
        )
        if token in text
    ]
    if len(scalar_members) == 1:
        return scalar_members[0]
    if len(scalar_members) > 1:
        return scalar_members
    # ``Any``, an absent annotation, and unions that cannot be represented by
    # this compact v0 mapper must remain unconstrained. Labelling them as
    # object rejects valid scalar/list values before the operation handler can
    # apply its domain-specific coercion.
    return None


def _compact_schema(value: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value[key]
        for key in (
            "id", "version", "kind", "summary", "thread", "side_effects",
            "reversible", "capabilities", "cost", "tags",
        )
        if key in value
    }


def _resolve_operation(value: str) -> str:
    return _tool_to_operation.get(str(value), str(value))


def _granted_capabilities() -> tuple[str, ...]:
    configured = _config.get("granted_capabilities", ["*"])
    if not isinstance(configured, (list, tuple)):
        return ("*",)
    return tuple(str(item) for item in configured)


def _execute(
    operation: str,
    arguments: Mapping[str, object] | None,
    *,
    expected_kind: OperationKind | None = None,
) -> dict[str, object]:
    try:
        value = _require_registry().execute(
            _resolve_operation(operation),
            arguments,
            capabilities=_granted_capabilities(),
            expected_kind=expected_kind,
        )
        return _ok({"operation": _resolve_operation(operation), "result": value})
    except OperationError as exc:
        return _error(exc)


def _require_registry() -> OperationRegistry:
    if _registry is None:
        raise OperationError("adapter.not_running", "MCP operation adapter is not running")
    return _registry


def _require_jobs() -> OperationJobRegistry:
    if _jobs is None:
        raise OperationError("adapter.not_running", "MCP operation job service is not running")
    return _jobs


def _ok(data: object) -> dict[str, object]:
    return {"ok": True, "data": data}


def _error(exc: Exception) -> dict[str, object]:
    if isinstance(exc, OperationError):
        return exc.envelope()
    return OperationError("adapter.failed", f"{type(exc).__name__}: {exc}").envelope()


__all__ = [
    "MAX_GATEWAY_TOOLS",
    "OWNER",
    "adapter_status",
    "operation_id_for_tool",
    "register_gateways",
    "shutdown_adapter",
]
