# Operations and agent workflow

Infernux MCP separates a stable MCP gateway surface from a discoverable catalog
of engine operations. An operation is not just a name: its `OperationSchema`
defines the complete contract an agent needs to call it safely.

![Agent operation workflow](media/agent-loop.png)

## Discover before acting

1. Call `host_capabilities` and `host_session_status` to understand the active
   project, mode, profile, catalog revision, and granted capabilities.
2. Use `operation_schema_search` to find operations by intent, domain, tag, or
   capability.
3. Use `operation_schema_get` to read the full argument and result contract.
4. Execute through the gateway matching the declared operation kind.
5. Validate the returned state and use the identities from that response in
   subsequent calls.

When the session or catalog revision changes, discard cached assumptions and
discover the relevant schemas again.

## Gateway kinds

- **Query** reads state without mutating project content.
- **Command** performs a bounded mutation through Editor transactions and Undo.
- **Workflow** coordinates a multi-stage engine task with structured progress.
- **Batch** executes compatible operations together and reports each result.
- **Job** runs long work, such as a Player build, without blocking the client;
  use the returned job ID to poll status or request cancellation.

The generic execution gateway is useful when a client has already inspected the
schema and wants the Host to dispatch by declared kind.

## Identities and component contracts

Assets are addressed by GUID rather than project paths. Scene queries return the
object and component identities required by later operations. Before writing an
unfamiliar component property, call `infernux.scene.component.schema`; it is the
authoritative description of field types, enum values, vector shapes, ranges,
and read-only fields.

Operation results and errors are structured for machines. Agents should report
the operation ID, returned identity, validation evidence, and any blocker rather
than inferring success from a tool call alone.
