# Usage

This package only exposes a handful of MCP tools. The actual work lives in operations.

![Calling an operation](media/agent-loop.png)

1. Search for the operation you need.
2. Read its schema. Do not guess argument names.
3. Call it as a query, a command, or a background job.
4. Keep using the IDs it returned. Assets are GUIDs. Scene objects come from queries.

Before writing an unfamiliar component field, call `infernux.scene.component.schema`.

Player builds and other slow work should go through `operation_job_submit`. Poll `operation_job_status` instead of waiting on the first call.
