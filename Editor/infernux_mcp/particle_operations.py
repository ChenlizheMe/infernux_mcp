"""Strict Particle Graph asset operations with AOT validation."""

from __future__ import annotations

from Infernux.engine.undo import UndoCommand
from Infernux.host import Operation, OperationError, OperationKind

from .operation_support import asset_path, on_editor, operation, set_json_pointer


def build_particle_operations() -> tuple[Operation, ...]:
    return (
        operation(
            "infernux.particle.graph.inspect",
            OperationKind.QUERY,
            "Read a strict Particle Graph document addressed by asset GUID.",
            _inspect_graph,
            capability="particle.read",
            input_properties={"asset_guid": {"type": "string"}},
            required=("asset_guid",),
            tags=("particle", "graph", "asset", "guid", "inspect"),
        ),
        operation(
            "infernux.particle.graph.property.set",
            OperationKind.COMMAND,
            "Set an existing Particle Graph document value and AOT-validate the result.",
            _set_graph_property,
            capability="particle.write",
            input_properties={
                "asset_guid": {"type": "string"},
                "pointer": {"type": "string"},
                "value": {},
            },
            required=("asset_guid", "pointer", "value"),
            side_effects=("Compiles and durably saves a Particle Graph asset with Undo support.",),
            reversible=True,
            tags=("particle", "graph", "property", "aot", "authoring"),
        ),
        operation(
            "infernux.particle.graph.document.replace",
            OperationKind.COMMAND,
            "Replace a Particle Graph with a complete strict schema document.",
            _replace_graph_document,
            capability="particle.write",
            input_properties={
                "asset_guid": {"type": "string"},
                "document": {"type": "object"},
            },
            required=("asset_guid", "document"),
            side_effects=("Compiles and durably replaces a Particle Graph asset with Undo support.",),
            reversible=True,
            tags=("particle", "graph", "document", "aot", "authoring"),
        ),
    )


def _inspect_graph(asset_guid: str) -> dict[str, object]:
    def read():
        from Infernux.particle.asset import ParticleGraphAsset

        path = asset_path(asset_guid, suffix=".particlegraph")
        graph = ParticleGraphAsset.load(path)
        return {
            "asset_guid": asset_guid,
            "path": path,
            "semantic_hash": graph.semantic_hash(),
            "document": graph.to_dict(),
        }

    return on_editor("infernux.particle.graph.inspect", read)


def _set_graph_property(asset_guid: str, pointer: str, value) -> dict[str, object]:
    def edit():
        from Infernux.particle.asset import ParticleGraphAsset

        path = asset_path(asset_guid, suffix=".particlegraph")
        before = ParticleGraphAsset.load(path)
        after = ParticleGraphAsset.from_dict(set_json_pointer(before.to_dict(), pointer, value))
        _commit_graph_change(path, asset_guid, before, after, f"Set Particle Graph {pointer}")
        return {
            "asset_guid": asset_guid,
            "path": path,
            "pointer": pointer,
            "semantic_hash": after.semantic_hash(),
            "document": after.to_dict(),
        }

    return on_editor("infernux.particle.graph.property.set", edit)


def _replace_graph_document(asset_guid: str, document: dict) -> dict[str, object]:
    def edit():
        from Infernux.particle.asset import ParticleGraphAsset

        path = asset_path(asset_guid, suffix=".particlegraph")
        before = ParticleGraphAsset.load(path)
        after = ParticleGraphAsset.from_dict(document)
        _commit_graph_change(path, asset_guid, before, after, "Replace Particle Graph Document")
        return {
            "asset_guid": asset_guid,
            "path": path,
            "semantic_hash": after.semantic_hash(),
            "document": after.to_dict(),
        }

    return on_editor("infernux.particle.graph.document.replace", edit)


def _commit_graph_change(path: str, guid: str, before, after, description: str) -> None:
    if before.to_dict() == after.to_dict():
        raise OperationError("particle.edit_rejected", "Particle Graph edit is unchanged.")

    from Infernux.engine.undo import UndoManager

    manager = UndoManager.instance()
    if manager is None or not manager.enabled or manager.is_executing:
        raise OperationError("particle.edit_rejected", "Editor history cannot accept Particle Graph edits.")
    command = _ParticleGraphDocumentCommand(
        path,
        guid,
        before,
        after,
        description,
    )
    if not manager.execute(command):
        raise OperationError("particle.edit_rejected", "Particle Graph edit failed validation or publication.")


class _ParticleGraphDocumentCommand(UndoCommand):
    """Publish one compiled graph atomically enough to recover a failed import."""

    marks_dirty = False

    def __init__(self, path: str, guid: str, before, after, description: str) -> None:
        super().__init__(description)
        self._path = str(path)
        self._guid = str(guid)
        self._before = before
        self._after = after

    def execute(self) -> None:
        self._apply(self._after, rollback=self._before)

    def undo(self) -> None:
        self._apply(self._before, rollback=self._after)

    def _apply(self, graph, *, rollback) -> None:
        try:
            self._publish(graph)
        except Exception:
            try:
                self._publish(rollback)
            except Exception:
                pass
            raise

    def _publish(self, graph) -> None:
        from Infernux.core.assets import AssetManager
        from Infernux.particle.artifact import ParticleArtifactRegistry

        ParticleArtifactRegistry.save_graph_asset(
            graph,
            self._path,
            guid=self._guid,
        )
        result = AssetManager.reimport_asset(self._path)
        if not result:
            result = AssetManager.import_asset(self._path)
        if not result:
            raise RuntimeError(
                str(getattr(result, "error", "Particle Graph import failed"))
            )


__all__ = ["build_particle_operations"]
