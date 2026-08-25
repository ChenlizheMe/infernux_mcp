"""Installable placeholder for the future MCP plugin migration."""

from Infernux.plugins import InxPlugin, PluginContext


class InfernuxCoreMcpPlugin(InxPlugin):
    """Own the MCP plugin lifecycle without starting services yet."""

    def preload(self, context: PluginContext) -> None:
        self.context = context

    def unload(self) -> None:
        self.context = None
