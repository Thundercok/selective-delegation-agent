"""
rat.plugins.manifest — Specifications and contracts for dynamic domain tool packs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ToolPackState(str, Enum):
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ERROR = "error"


@dataclass
class ToolPackManifest:
    """Metadata describing a modular domain tool pack."""

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "vertical"  # "vertical" | "domain" | "utility"
    author: str = "RAT Team"
    enabled_by_default: bool = False
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class ToolPack(ABC):
    """Abstract base class for built-in and external domain plugins / tool packs."""

    manifest: ToolPackManifest

    @abstractmethod
    def create_capabilities(self, context: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Return list of Capability instances to be registered into CapabilityRegistry."""
        ...

    def get_view_factories(self) -> Dict[str, Callable]:
        """Return mapping of artifact_kind -> view_factory callable for UI projections."""
        return {}

    def get_ui_cards(self) -> List[Dict[str, Any]]:
        """Return optional QtQuick desk view or artifact card specs contributed by this pack.

        Each dict may declare:
            - ``id``: stable identifier (e.g. ``"reading_desk"``)
            - ``name``: display label for menus
            - ``qml``: absolute filesystem path or ``file://`` URL to a QML component
            - ``kind``: ``"view"`` (full desk view, default) or ``"artifact_card"``
            - ``visual_types``: list of ``visual_type`` strings handled (for ``"artifact_card"``)
        """
        return []

    def get_routing_keywords(self) -> Tuple[str, ...]:
        """Return lowercase trigger keywords used for lazy pack auto-loading."""
        return ()

    def get_slash_commands(self) -> Dict[str, str]:
        """Return mapping of slash command (e.g. ``'/reading'``) -> view ``id``."""
        return {}

    def get_instant_handlers(
        self,
    ) -> List[Callable[[str], Optional[Tuple[Dict[str, Any], str]]]]:
        """Return instant query handlers returning ``(artifact_card_dict, answer_text)`` or ``None``."""
        return []

    def create_ui_coordinator(self, controller: Any) -> Optional[Any]:
        """Return an optional UI coordinator instance bound to ``controller`` for this pack."""
        return None

    def on_loaded(self, registry: Any) -> None:
        """Lifecycle hook invoked immediately after capabilities are registered."""
        pass

    def on_unloaded(self, registry: Any) -> None:
        """Lifecycle hook invoked immediately after capabilities are unregistered."""
        pass
