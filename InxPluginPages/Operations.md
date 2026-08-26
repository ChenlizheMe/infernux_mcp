# Operation catalog

The MCP surface advertises a small set of gateway tools. Engine actions live behind those gateways as formal OperationSchema documents.

- Search schemas by domain or capability before execution.
- Fetch a complete schema only when its argument contract is needed.
- Address existing assets by GUID.
- Treat session and revision changes as schema-discovery boundaries.
- Use command gateways for mutations and query gateways for read-only inspection.
- Submit long-running Player builds through the job gateway.
- Inspect component field contracts with `infernux.scene.component.schema` before writing unfamiliar values.

Scene, component, asset, material, particle, camera, runtime, input, semantic UI,
render capture, Console, documentation, Player build and validation, checkpoint, and
supervisor operations are registered during preload.
