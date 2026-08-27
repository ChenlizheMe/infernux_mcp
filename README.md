# Infernux MCP

Let an MCP-compatible AI agent drive the Infernux Editor.

The package starts a local server inside the Editor at `http://127.0.0.1:9713/mcp`. From there an agent can inspect the project, edit the scene, enter Play Mode, and capture what the game actually rendered.

![Infernux MCP](InxPluginPages/media/system-overview.png)

New projects include this package. Turn it off or uninstall it from the Plugins window if you do not want it.

## Features

- Inspect and edit scene objects, components, materials, particles, and cameras
- Play, pause, step, and stop
- Inject keyboard and pointer input
- Capture Scene / Game views (engine frames, not desktop screenshots)
- Build and talk to a standalone Debug Player

## Setup

Point your MCP client at `http://127.0.0.1:9713/mcp`. Only localhost is accepted. Change the port with `INFERNUX_MCP_PORT` before launching the Editor.

## Talking to it

Begin with `host_session_status`. Fetch `operation_schema_list` once with `limit: 200`, cache the compact catalog, and refresh it only when the reported revision changes. Search for an operation, read its full schema only when needed, then execute:

```json
{
  "tool": "operation_schema_search",
  "arguments": {"query": "scene object create", "limit": 10}
}
```

```json
{
  "tool": "operation_command_execute",
  "arguments": {
    "operation": "infernux.scene.object.create",
    "arguments": {"kind": "cube", "name": "AgentCube"}
  }
}
```

Do not invent field names. Ask `infernux.scene.component.schema` first. Slow work such as a Player build should go through `operation_job_submit`.

Group known, ordered calls with `operation_batch_execute` instead of paying for one transport round trip per operation. If an operation returns `mode_required`, its error details include the exact argument vector the agent should run to switch modes. A Supervisor-managed Editor is restarted and verified automatically; an unmanaged Editor must be reopened after its project policy is changed.

## Requirements

Infernux `0.3.7` or later in the `0.3.x` line.
