"""
tests/test_plugin_tool_packs.py — Verification of decoupled built-in and external tool packs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from rat.engine.assistant_runtime import AssistantRuntime
from rat.kernel.capabilities import build_core_registry
from rat.kernel.registry import Capability, OperationDefinition
from rat.plugins import PluginManager, ToolPack, ToolPackManifest, get_plugin_manager


class _DummyExternalPack(ToolPack):
    """Minimal synthetic external plugin used to verify dynamic host lifecycle."""

    manifest = ToolPackManifest(
        id="dummy_external",
        name="Dummy External Pack",
        description="Synthetic plugin for host contract verification.",
        version="0.1.0",
        category="vertical",
    )

    def create_capabilities(self, context: Optional[Dict[str, Any]] = None) -> List[Any]:
        cap = Capability("dummy_cap", "Dummy", "Synthetic external capability")
        cap.register_operation(
            OperationDefinition(
                name="dummy_echo",
                description="Echo supplied value.",
                parameters={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
                handler=lambda args, **_ctx: {"echoed": args["value"]},
                artifact_kind="dummy_echo",
            )
        )
        return [cap]

    def get_routing_keywords(self):
        return ("dummy_trigger",)

    def get_slash_commands(self):
        return {"/dummy": "dummy_view"}

    def get_ui_cards(self):
        return [{"id": "dummy_view", "name": "Dummy View", "kind": "view", "qml": ""}]

    def get_instant_handlers(self):
        def _handle(q: str):
            if "dummy_instant" in q.lower():
                return {"visual_type": "dummy_card", "value": q}, f"Dummy handled: {q}"
            return None

        return [_handle]


def test_core_registry_has_no_domain_verticals():
    """Verify that build_core_registry creates a pure General Reasoning Desktop Shell."""
    core = build_core_registry()
    op_names = {op.name for op in core.list_operations()}

    assert "search_documents" in op_names
    assert "read_document" in op_names
    assert "open_document" in op_names
    assert "deliver_document" in op_names
    assert "open_application" in op_names
    assert "compose_result_table" in op_names
    assert "update_task_state" in op_names
    assert "calculate" in op_names
    assert "inspect_artifact" in op_names

    # Specialized domain verticals must NOT be hard-wired into core
    assert "get_schedule" not in op_names
    assert "get_group_availability" not in op_names
    assert "locate_room" not in op_names


def test_dynamic_pack_loading_and_unloading():
    """Verify that built-in and external packs load and unload dynamically via PluginManager."""
    manager = PluginManager()
    manager.register_builtins()
    manager.register_pack(_DummyExternalPack())
    registry = build_core_registry()

    # 1. External pack
    assert not manager.is_pack_loaded("dummy_external", registry)
    assert manager.load_pack("dummy_external", registry)
    assert manager.is_pack_loaded("dummy_external", registry)
    assert "dummy_echo" in [op.name for op in registry.list_operations()]

    assert manager.unload_pack("dummy_external", registry)
    assert not manager.is_pack_loaded("dummy_external", registry)
    assert "dummy_echo" not in [op.name for op in registry.list_operations()]


def test_assistant_runtime_core_mode_and_dynamic_load():
    """Verify AssistantRuntime starting in pure core mode can dynamically load an external pack."""
    manager = get_plugin_manager()
    manager.register_pack(_DummyExternalPack())
    try:
        runtime = AssistantRuntime(active_tool_packs=[], use_live_model=False)
        assert not runtime.is_tool_pack_loaded("dummy_external")
        assert not runtime.registry.has_operation("dummy_echo")

        assert runtime.load_tool_pack("dummy_external")
        assert runtime.is_tool_pack_loaded("dummy_external")
        assert runtime.registry.has_operation("dummy_echo")

        res = runtime.dispatcher.execute_operation("dummy_echo", {"value": "ok"})
        assert res.status == "success"
        assert res.artifact.payload["echoed"] == "ok"

        runtime.unload_tool_pack("dummy_external")
        assert not runtime.is_tool_pack_loaded("dummy_external")
        assert not runtime.registry.has_operation("dummy_echo")

        failed = runtime.dispatcher.execute_operation("dummy_echo", {"value": "ok"})
        assert failed.status == "error"
    finally:
        manager.unregister_pack("dummy_external")


def test_quick_pdf_controller_opens_external_plugin_view_and_instant_dispatch():
    """Verify QuickPDFController opens dynamic plugin views and dispatches plugin instant handlers."""
    from rat.ui.quick_pdf_controller import QuickPDFController

    manager = get_plugin_manager()
    manager.register_pack(_DummyExternalPack())
    controller = QuickPDFController(auto_init_finder=False)
    controller.ready()
    try:
        assert controller.openPluginView("dummy_view") is True
        assert controller.snapshot["view"] == "plugin"
        assert controller.snapshot["activePluginView"]["id"] == "dummy_view"
        assert controller.assistant_runtime.is_tool_pack_loaded("dummy_external")

        controller.closePluginView()
        assert controller.snapshot["view"] != "plugin"

        handled = controller.submit("chạy dummy_instant ngay")
        assert handled is True
        assert controller.snapshot["artifactCard"]["visual_type"] == "dummy_card"
    finally:
        controller.close()
        manager.unregister_pack("dummy_external")
