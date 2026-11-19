"""
rat.plugins.packs — Built-in general-purpose tool packs.

Domain-specific verticals (e.g. archetypal symbolic systems) are loaded externally
via the ``rat.plugins`` entry-point group.
"""
from rat.plugins.packs.timetable import TimetableToolPack

__all__ = [
    "TimetableToolPack",
]
