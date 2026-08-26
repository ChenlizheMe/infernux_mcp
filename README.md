# Infernux MCP

`infernux/mcp` is the default, uninstallable MCP Host integration for the
Infernux editor. It owns the HTTP transport, session/workflow implementation,
and the OperationSchema-to-MCP adapter; the engine core contains only the
transport-neutral Host registry and owner-thread dispatcher.

The default MCP surface exposes only schema discovery, execution, batch,
workflow, job, capability, and session gateways. Behind those gateways the
package owns formal operations for project/session state, scene and component
authoring, GUID-addressed assets, materials, strict Particle Graph documents,
editor/game cameras, and Play Mode. Every engine capability is implemented
directly as an `OperationSchema`; there is no alternate flat-tool
implementation or compatibility mapping. The package lives entirely under
`Editor/`, so it is excluded from Player builds.

## Lifecycle

`InfernuxMCPPreload` is discovered through the engine-wide `InxPreload` AST
scan; there is no manifest entry point. Loading starts the loopback HTTP
transport and registers the operations owned by `infernux/mcp`. Unloading
stops accepting requests, drains or cancels bounded jobs, stops the transport,
removes owned operations and generated client-discovery entries, and releases
the port. User-owned entries in shared MCP configuration files are preserved.

Installing the package creates project-local code under
`Packages/infernux/mcp/Editor`. Uninstalling it does not make the engine install
it again on normal startup. A new project installs it from the engine's
`default-libraries.json`; an explicit reinstall may use the verified offline
artifact cache.

## Gateway model

The default surface has 14 tools:

- `operation_schema_list`, `operation_schema_get`, and
  `operation_schema_search` discover OperationSchema v0 documents;
- `operation_query_execute`, `operation_command_execute`,
  `operation_workflow_invoke`, `operation_execute`, and
  `operation_batch_execute` invoke them;
- `operation_job_submit`, `operation_job_status`, and
  `operation_job_cancel` handle bounded asynchronous work;
- `mcp_ping`, `host_capabilities`, and `host_session_status` expose connection
  and revision state.

For example, first search for a checkpoint capability:

```json
{
  "tool": "operation_schema_search",
  "arguments": {"query": "checkpoint", "limit": 20}
}
```

Then invoke the returned stable operation ID through the matching gateway:

```json
{
  "tool": "operation_query_execute",
  "arguments": {
    "operation": "infernux.mcp.checkpoint.list",
    "arguments": {}
  }
}
```

The operation catalog is intentionally discovered at runtime. Clients should
search by domain, fetch only the complete schemas they need, then execute the
stable dotted IDs. Existing assets are addressed by GUID; paths are returned
as context and are accepted only where a new destination must be chosen.
Scene/component edits enter the editor's shared Undo journal, material edits
use the editable-resource transaction, and Particle Graph edits must pass the
strict document parser and AOT compiler before publication. Switching profiles
remains a Supervisor-controlled process boundary; clients must rediscover
schemas after revision/session changes.
