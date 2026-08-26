# Notes

This is a local development hook, not a public server. It only binds to localhost.

![Local-only access](media/trust-gates.png)

Every call is checked against the operation schema and `ProjectSettings/mcp_capabilities.json`. Scene edits go through the Editor's normal undo stack.

Screenshots come from the engine's Scene / Game views, never from the desktop.

A few short-lived tokens exist for shutting down the Editor, locking the current project, and talking to a Debug Player. Status calls never return the secret itself.
