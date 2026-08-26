# Infernux MCP

Infernux MCP connects MCP-compatible AI agents to the Infernux Editor. It lets
an agent inspect a project, author scenes and assets, control Play Mode, drive
the Editor through synthetic input, observe semantic UI state, capture engine
render targets, and validate a standalone Player.

The package is installed as the `infernux/mcp` InxPackage and runs only in the
Editor. It starts a loopback MCP endpoint for the active project and stops with
the project session.

## Capabilities

- inspect and edit scene objects, components, transforms, materials, particle
  graphs, cameras, and GUID-addressed assets;
- enter, pause, step, resume, and stop Play Mode;
- inject keyboard, pointer, wheel, and text input through the engine event path;
- inspect rendered controls through semantic UI snapshots;
- read bounded Editor Console snapshots;
- request Scene or Game render-target captures and GPU object picks;
- launch, observe, capture, inspect logs from, and shut down a managed Debug
  Player;
- build standalone Player packages through the job gateway;
- manage validation attempts, checkpoints, traces, and blocker reports.

## Installation

Install `infernux/mcp` from the Infernux Package Manager or import the provided
`.inxpkg` file. New projects may include it in their default library set. The
package can be disabled, uninstalled, or installed again like any other
InxPackage.

The Editor exposes the MCP endpoint on `http://127.0.0.1:9713/mcp` by default.
Set `INFERNUX_MCP_HOST` or `INFERNUX_MCP_PORT` before launching the Editor to
change the binding.

## Using the MCP surface

Clients discover operation schemas, then invoke the selected stable operation
ID through a query, command, workflow, batch, or job gateway.

Search for an operation:

```json
{
  "tool": "operation_schema_search",
  "arguments": {"query": "scene object create", "limit": 10}
}
```

Execute the returned command:

```json
{
  "tool": "operation_command_execute",
  "arguments": {
    "operation": "infernux.scene.object.create",
    "arguments": {"kind": "cube", "name": "AgentCube"}
  }
}
```

Existing assets are addressed by GUID. Scene objects and components use the
identities returned by scene queries. Commands that modify project content use
the Editor's normal transaction and Undo services.

Long-running work such as `infernux.player.build` should be submitted with
`operation_job_submit` and polled with `operation_job_status`. Component
properties can be discovered with `infernux.scene.component.schema`; this is
also the authoritative source for enum values, vector shapes, ranges, and
read-only fields.

Editor input, semantic UI observation, and Editor render capture are available
in a Supervisor-managed `global_validation` session. Standalone Debug Player
validation can also run in `developer_assist` when the corresponding Player
capabilities are granted. Render captures contain engine render-target pixels
and are written as review artifacts; desktop or operating-system screen capture
is never used.

## Package layout

- `Editor/infernux_mcp` contains the MCP server and operation adapters;
- `InxPluginPages` provides Package Manager documentation;
- `InxPackage.json` defines the `infernux/mcp` package.

This package requires Infernux `>=0.3.7,<0.4`.
