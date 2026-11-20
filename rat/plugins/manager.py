"""
rat.plugins.manager — Dynamic tool pack discovery, registration, and lifecycle management.

Supports both built-in packs and external Python packages declaring the
``rat.plugins`` entry-point group (plus optional ``RAT_PLUGIN_MODULES``).
"""
from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rat.plugins.manifest import ToolPack, ToolPackManifest

logger = logging.getLogger("rat.plugins")

EXTERNAL_PLUGIN_ENTRY_POINT_GROUP = "rat.plugins"


def _to_qml_url(qml_path: str) -> str:
    if not qml_path:
        return ""
    if qml_path.startswith("file://"):
        return qml_path
    p = Path(qml_path)
    if p.is_absolute():
        return p.as_uri()
    return qml_path


class PluginManager:
    """Central manager for discovering, registering, and dynamically toggling domain tool packs."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._packs: Dict[str, ToolPack] = {}
        self._pack_caps: Dict[str, Set[str]] = {}
        self._listeners: List[Callable[[str, str], None]] = []

    def register_pack(self, pack: ToolPack) -> None:
        """Register a tool pack with the manager."""
        with self._lock:
            self._packs[pack.manifest.id] = pack
            logger.debug(
                "PluginManager: Registered tool pack '%s' (%s)",
                pack.manifest.id,
                pack.manifest.name,
            )

    def unregister_pack(self, pack_id: str) -> Optional[ToolPack]:
        """Unregister a tool pack from the manager."""
        with self._lock:
            pack = self._packs.pop(pack_id, None)
            self._pack_caps.pop(pack_id, None)
            return pack

    def get_pack(self, pack_id: str) -> Optional[ToolPack]:
        """Look up a tool pack by ID."""
        with self._lock:
            return self._packs.get(pack_id)

    def list_packs(self) -> List[ToolPack]:
        """Return all registered tool packs."""
        with self._lock:
            return list(self._packs.values())

    def list_manifests(self) -> List[ToolPackManifest]:
        """Return manifests of all available tool packs."""
        with self._lock:
            return [p.manifest for p in self._packs.values()]

    def is_pack_loaded(self, pack_id: str, registry: Any) -> bool:
        """Check if a tool pack's capabilities are currently loaded into a given registry."""
        with self._lock:
            caps = self._pack_caps.get(pack_id)
            if not caps or not hasattr(registry, "get_capability"):
                return False
            return any(registry.get_capability(cap_name) is not None for cap_name in caps)

    def load_pack(
        self,
        pack_id: str,
        registry: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Dynamically load a tool pack into a CapabilityRegistry."""
        with self._lock:
            pack = self._packs.get(pack_id)
            if pack is None:
                logger.warning("PluginManager: Tool pack '%s' not found.", pack_id)
                return False

            if self.is_pack_loaded(pack_id, registry):
                logger.debug("PluginManager: Tool pack '%s' is already loaded.", pack_id)
                return True

            try:
                capabilities = pack.create_capabilities(context=context)
                registered_cap_names: Set[str] = set()
                view_factories = pack.get_view_factories()

                for cap in capabilities:
                    if hasattr(registry, "register_capability"):
                        registry.register_capability(cap)
                        registered_cap_names.add(cap.name)

                        if view_factories:
                            for op in cap.operations.values():
                                if op.artifact_kind in view_factories:
                                    op.view_factory = view_factories[op.artifact_kind]

                self._pack_caps.setdefault(pack_id, set()).update(registered_cap_names)
                pack.on_loaded(registry)
                self._notify_listeners(pack_id, "loaded")
                logger.info(
                    "PluginManager: Loaded tool pack '%s' (%d capabilities).",
                    pack_id,
                    len(capabilities),
                )
                return True
            except Exception as e:
                logger.error("PluginManager: Failed to load tool pack '%s': %s", pack_id, e, exc_info=True)
                return False

    def unload_pack(self, pack_id: str, registry: Any) -> bool:
        """Dynamically unload a tool pack from a CapabilityRegistry."""
        with self._lock:
            pack = self._packs.get(pack_id)
            if pack is None:
                return False

            cap_names = self._pack_caps.pop(pack_id, set())
            unregistered_any = False

            if hasattr(registry, "unregister_capability"):
                for cap_name in cap_names:
                    removed = registry.unregister_capability(cap_name)
                    if removed is not None:
                        unregistered_any = True

            pack.on_unloaded(registry)
            self._notify_listeners(pack_id, "unloaded")
            logger.info("PluginManager: Unloaded tool pack '%s'.", pack_id)
            return unregistered_any

    def add_listener(self, callback: Callable[[str, str], None]) -> None:
        """Register a listener for pack load/unload events: callback(pack_id, event)."""
        with self._lock:
            self._listeners.append(callback)

    def _notify_listeners(self, pack_id: str, event: str) -> None:
        for cb in list(self._listeners):
            try:
                cb(pack_id, event)
            except Exception as e:
                logger.debug("PluginManager listener error: %s", e)

    def get_ui_views(self) -> List[Dict[str, Any]]:
        """Collect all full-desk plugin views across registered packs."""
        views: List[Dict[str, Any]] = []
        with self._lock:
            for pack in self._packs.values():
                for spec in pack.get_ui_cards():
                    if spec.get("kind", "view") != "view":
                        continue
                    entry = dict(spec)
                    entry["pack_id"] = pack.manifest.id
                    entry["qml_url"] = _to_qml_url(str(spec.get("qml") or ""))
                    views.append(entry)
        return views

    def get_artifact_card_qml_map(self) -> Dict[str, str]:
        """Return mapping of ``visual_type -> file://...qml`` from registered packs."""
        mapping: Dict[str, str] = {}
        with self._lock:
            for pack in self._packs.values():
                for spec in pack.get_ui_cards():
                    if spec.get("kind") != "artifact_card":
                        continue
                    url = _to_qml_url(str(spec.get("qml") or ""))
                    for vt in spec.get("visual_types") or ():
                        mapping[str(vt)] = url
        return mapping

    def get_routing_keywords_map(self) -> List[Tuple[str, Tuple[str, ...]]]:
        """Return list of ``(pack_id, keywords)`` for lazy pack auto-loading."""
        result: List[Tuple[str, Tuple[str, ...]]] = []
        with self._lock:
            for pack in self._packs.values():
                kws = tuple(pack.get_routing_keywords() or ())
                if kws:
                    result.append((pack.manifest.id, kws))
        return result

    def get_slash_command_map(self) -> Dict[str, Dict[str, str]]:
        """Return mapping of ``'/cmd' -> {'pack_id': ..., 'view_id': ...}``."""
        mapping: Dict[str, Dict[str, str]] = {}
        with self._lock:
            for pack in self._packs.values():
                for cmd, view_id in (pack.get_slash_commands() or {}).items():
                    mapping[str(cmd).strip().lower()] = {
                        "pack_id": pack.manifest.id,
                        "view_id": str(view_id),
                    }
        return mapping

    def get_instant_handlers(self) -> List[Tuple[str, Callable[[str], Optional[Tuple[Dict[str, Any], str]]]]]:
        """Return list of ``(pack_id, handler)`` for instant query dispatch."""
        handlers: List[Tuple[str, Callable[[str], Optional[Tuple[Dict[str, Any], str]]]]] = []
        with self._lock:
            for pack in self._packs.values():
                for fn in pack.get_instant_handlers() or ():
                    handlers.append((pack.manifest.id, fn))
        return handlers

    def _register_pack_factory(self, factory: Any, source_label: str) -> None:
        try:
            instance = factory() if isinstance(factory, type) or callable(factory) else factory
            if isinstance(instance, ToolPack):
                self.register_pack(instance)
            else:
                logger.warning("PluginManager: Ignoring non-ToolPack plugin from %s", source_label)
        except Exception as exc:
            logger.warning("PluginManager: Failed to instantiate external plugin %s: %s", source_label, exc)

    def discover_external_plugins(self) -> None:
        """Discover external ToolPacks via ``rat.plugins`` entry points and ``RAT_PLUGIN_MODULES``."""
        if os.environ.get("RAT_DISABLE_EXTERNAL_PLUGINS", "").strip().lower() in ("1", "true", "yes"):
            return

        try:
            eps = importlib.metadata.entry_points(group=EXTERNAL_PLUGIN_ENTRY_POINT_GROUP)
        except Exception as exc:
            logger.debug("PluginManager: entry_points lookup failed: %s", exc)
            eps = ()

        for ep in eps:
            try:
                loaded = ep.load()
                self._register_pack_factory(loaded, f"entry_point:{ep.name}")
            except Exception as exc:
                logger.warning("PluginManager: Failed loading entry point '%s': %s", ep.name, exc)

        extra_modules = os.environ.get("RAT_PLUGIN_MODULES", "").strip()
        if extra_modules:
            for spec in (s.strip() for s in extra_modules.split(",") if s.strip()):
                try:
                    mod_name, _, attr = spec.partition(":")
                    mod = importlib.import_module(mod_name)
                    target = getattr(mod, attr) if attr else getattr(mod, "get_tool_pack")
                    self._register_pack_factory(target, f"module:{spec}")
                except Exception as exc:
                    logger.warning("PluginManager: Failed loading module plugin '%s': %s", spec, exc)

    def register_builtins(self) -> None:
        """Discover installed external plugins (no domain verticals are bundled in core)."""
        with self._lock:
            self.discover_external_plugins()


_DEFAULT_PLUGIN_MANAGER: Optional[PluginManager] = None
_INIT_LOCK = threading.Lock()


def get_plugin_manager() -> PluginManager:
    """Retrieve the global PluginManager singleton with built-ins & external plugins registered."""
    global _DEFAULT_PLUGIN_MANAGER
    if _DEFAULT_PLUGIN_MANAGER is None:
        with _INIT_LOCK:
            if _DEFAULT_PLUGIN_MANAGER is None:
                manager = PluginManager()
                manager.register_builtins()
                _DEFAULT_PLUGIN_MANAGER = manager
    return _DEFAULT_PLUGIN_MANAGER


def reset_plugin_manager() -> None:
    """Reset the global PluginManager singleton (primarily for isolated tests)."""
    global _DEFAULT_PLUGIN_MANAGER
    with _INIT_LOCK:
        _DEFAULT_PLUGIN_MANAGER = None
