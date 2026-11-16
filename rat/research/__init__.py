"""Read-only helpers for the NCKH research repo (run logs, intervention files).

RAT reads files from the research repo and never writes into it. Everything RAT
produces for research (labels, paper index copies) lives under ``RAT_DIR``.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_RESEARCH_REPO = Path.home() / "Documents" / "Github" / "multi-step-structured-reasoning"


def research_repo() -> Path:
    return Path(os.environ.get("RAT_RESEARCH_REPO") or DEFAULT_RESEARCH_REPO).expanduser()
