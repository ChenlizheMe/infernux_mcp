# Infernux MCP

Infernux MCP is the local control plane that connects MCP-compatible AI agents
to the Infernux Editor. It gives an agent a typed, inspectable way to understand
a project, author content, run the game, and collect evidence from the Editor or
a standalone Debug Player.

![Infernux MCP system overview](InxPluginPages/media/system-overview.png)

The package is installed as `infernux/mcp`. It runs inside the Editor, uses the
Engine's authoritative APIs and identity systems, and starts a project-scoped
MCP endpoint at `http://127.0.0.1:9713/mcp` by default.

## Why schema gateways

The MCP surface stays small and stable. The actual engine capabilities are
published as versioned `OperationSchema` contracts behind a set of gateways.
Each schema describes:

- whether the operation is a query, command, workflow, or long-running job;
- its typed JSON arguments and result;
- the capability required to invoke it;
- expected side effects, reversibility, cost, and structured errors.

An agent searches only the relevant portion of the catalog and fetches a full
contract before invoking an unfamiliar operation. This keeps the initial model
context bounded while allowing the engine and installed plugins to contribute
new operations without expanding the MCP tool list for every capability.

![Agent work cycle](InxPluginPages/media/agent-loop.png)

A reliable agent workflow is:

1. inspect host capabilities and the current session;
2. search the schema catalog for the intended action;
3. read the selected operation's complete contract;
4. execute through the matching query, command, workflow, batch, or job gateway;
5. validate the result through state queries, logs, semantic UI, or render captures;
6. save, checkpoint, or report the result, then rediscover schemas when their
   revision changes.

Existing assets are addressed by GUID. Scene objects and components use the
identities returned by scene queries. Project mutations pass through the
Editor's normal transaction and Undo services instead of editing internal state
behind the Editor's back.

## Trust model and control tokens

Infernux MCP is a local development interface, not a network service. The host
accepts loopback bindings only. Every operation is then checked against its
schema, JSON contract, operation kind, and the project's capability policy in
`ProjectSettings/mcp_capabilities.json`.

![Infernux MCP trust gates](InxPluginPages/media/trust-gates.png)

Three short-lived secrets protect privileged process boundaries:

- **Supervisor lease** — proves that a normal Editor shutdown request came from
  the Supervisor that owns the session.
- **Project lock token** — binds the Editor process, project path, endpoint, and
  session identity so a Supervisor can safely attach to or resume the correct
  project.
- **Player control token** — generated for each Debug Player launch and required
  on its bounded input, observation, capture, log, motion, and shutdown channel.

Secrets are not returned by public status operations. Status responses expose
only whether a credential is configured and, where useful, a short SHA-256
fingerprint for identity comparison. These tokens authenticate sensitive
control channels; they do not bypass operation schemas or capability checks.

See [Trust gates](InxPluginPages/Trust.md) for the complete boundary model.

## What an agent can do

- inspect and edit scene objects, components, transforms, materials, particle
  graphs, cameras, and GUID-addressed assets;
- enter, pause, step, resume, and stop Play Mode;
- inject keyboard, pointer, wheel, and text input through the engine event path;
- inspect rendered controls through semantic UI snapshots;
- read bounded Editor Console snapshots and engine documentation;
- request Scene or Game render-target captures and GPU object picks;
- build, launch, observe, capture, inspect logs from, and shut down a managed
  standalone Debug Player;
- manage validation attempts, checkpoints, traces, and blocker reports.

Editor input, semantic UI observation, and Editor render capture require a
Supervisor-managed `global_validation` session. Standalone Debug Player
validation is also available to `developer_assist` when the corresponding
Player capabilities are granted. Captures always come from engine render
targets; the package never falls back to operating-system desktop capture.

## Quick start

Search for an operation:

```json
{
  "tool": "operation_schema_search",
  "arguments": {"query": "scene object create", "limit": 10}
}
```

Fetch the returned operation's full schema before relying on its arguments,
then execute it through the matching gateway:

```json
{
  "tool": "operation_command_execute",
  "arguments": {
    "operation": "infernux.scene.object.create",
    "arguments": {"kind": "cube", "name": "AgentCube"}
  }
}
```

Long-running operations such as `infernux.player.build` should be submitted
with `operation_job_submit` and polled with `operation_job_status`. Before
writing unfamiliar component properties, use
`infernux.scene.component.schema` to discover field types, enum values, vector
shapes, ranges, and read-only fields.

## Installation

Install `infernux/mcp` from the Infernux Package Manager or import its `.inxpkg`
file. New projects may include it in their default library set. Like any other
InxPackage, it can be disabled, uninstalled, and installed again.

The endpoint defaults to `http://127.0.0.1:9713/mcp`. Set
`INFERNUX_MCP_HOST` to another loopback address or `INFERNUX_MCP_PORT` to a
different port before launching the Editor. Non-loopback hosts are rejected.

## Package layout

- `Editor/infernux_mcp` contains the MCP server, operation catalog, adapters,
  and Editor integration;
- `InxPluginPages` contains Package Manager documentation and media;
- `InxPackage.json` defines the `infernux/mcp` package.

This package requires Infernux `>=0.3.7,<0.4`.
