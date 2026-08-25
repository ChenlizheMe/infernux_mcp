# Infernux MCP

`infernux/mcp` is the default, uninstallable MCP Host integration for the
Infernux editor. It owns the HTTP transport, session/workflow implementation,
and the OperationSchema-to-MCP adapter; the engine core contains only the
transport-neutral Host registry and owner-thread dispatcher.

The default MCP surface exposes a small set of schema discovery, execution,
batch, workflow, job, capability, and session gateways. Engine domains are
registered as operations instead of hundreds of top-level MCP tools. The
package lives entirely under `Editor/`, so it is excluded from Player builds.

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

For example, first search for a capability:

```json
{
  "tool": "operation_schema_search",
  "arguments": {"query": "particle graph", "limit": 20}
}
```

Then invoke the returned stable operation ID through the matching gateway:

```json
{
  "tool": "operation_command_execute",
  "arguments": {
    "operation": "infernux.particle.graph.add.node",
    "arguments": {"stage": "update", "type_id": "particle.attribute.orientation"}
  }
}
```

`developer_assist` owns direct authoring/build operations. The disjoint
`global_validation` profile observes a running Player and interacts through
the real input path. Switching profiles is a Supervisor-controlled process
boundary; clients must rediscover schemas after the revision/session changes.
