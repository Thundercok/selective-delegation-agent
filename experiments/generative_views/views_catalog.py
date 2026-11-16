"""Component catalog for the generative-view experiment (2026-11-16).

The model composes a screen from these blocks. Data enters a block only by
reference (``*_field`` paths into the payload, ``*_key`` names inside list
items), never as copied values, so a layout can be ugly but numbers can't be
made up. Literal text is allowed only in ``LITERAL_KEYS``.

Not wired into rat/: this is an experiment. rat/kernel/view_spec.py is the
production contract and still copies values into blocks.
"""
from __future__ import annotations

import re
from typing import Any

LITERAL_KEYS = {"title", "label", "unit", "text"}

BLOCKS: dict[str, dict[str, Any]] = {
    "summary": {
        "doc": "Heading and one line of text. text_field (optional) points at a string in the payload.",
        "required": ["title"], "optional": ["text", "text_field"],
    },
    "stat": {
        "doc": "One big number with a label, e.g. the latest bill. value_field points at a number.",
        "required": ["value_field", "label"], "optional": ["unit"],
    },
    "card_grid": {
        "doc": "Grid of cards that can be shown face up or face down and flipped (tarot, flashcards).",
        "required": ["items_field", "title_key"],
        "optional": ["subtitle_key", "body_key", "face", "per_row"],
    },
    "metric_chart": {
        "doc": "Bar or line chart over a list: x_key for the axis, y_key for the value.",
        "required": ["items_field", "x_key", "y_key", "kind"], "optional": ["unit", "title"],
    },
    "table": {
        "doc": "Table over a list. columns: [{key, label}].",
        "required": ["items_field", "columns"], "optional": ["title"],
    },
    "quiz": {
        "doc": "Multiple-choice questions with an answer hidden until the user submits.",
        "required": ["items_field", "prompt_key", "choices_key", "answer_key"],
        "optional": ["source_key", "title"],
    },
    "actions": {
        "doc": "Buttons. action_ids must come from the allowed list.",
        "required": ["action_ids"], "optional": [],
    },
}


def resolve(payload: Any, path: str) -> Any:
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def validate(spec: Any, payload: dict, allowed_actions: list[str]) -> list[str]:
    """Structural check. Returns the list of problems; empty means it can render."""
    if not isinstance(spec, dict) or not isinstance(spec.get("title"), str):
        return ["spec must be an object with a string title"]
    blocks = spec.get("blocks")
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= 8:
        return ["blocks must be a list of 1-8 blocks"]
    errors = []
    for i, block in enumerate(blocks):
        where = f"block {i}"
        btype = block.get("type") if isinstance(block, dict) else None
        if btype not in BLOCKS:
            errors.append(f"{where}: unknown type {btype!r}")
            continue
        data = block.get("data")
        if not isinstance(data, dict):
            errors.append(f"{where} ({btype}): data must be an object")
            continue
        rule = BLOCKS[btype]
        for key in rule["required"]:
            if key not in data:
                errors.append(f"{where} ({btype}): missing {key}")
        for key in set(data) - set(rule["required"]) - set(rule["optional"]):
            errors.append(f"{where} ({btype}): unexpected key {key}")
        items = None
        for key, ref in data.items():
            if key.endswith("_field"):
                try:
                    value = resolve(payload, ref)
                except (KeyError, TypeError):
                    errors.append(f"{where} ({btype}): {key}={ref!r} not in payload")
                    continue
                if key == "items_field":
                    if not (isinstance(value, list) and value and all(isinstance(v, dict) for v in value)):
                        errors.append(f"{where} ({btype}): {ref!r} is not a list of records")
                    else:
                        items = value
                if key == "value_field" and not isinstance(value, (int, float)):
                    errors.append(f"{where} ({btype}): {ref!r} is not a number")
        if items is not None:
            keys = [data[k] for k in data if k.endswith("_key")]
            columns = data.get("columns") if btype == "table" else []
            if not isinstance(columns, list):
                errors.append(f"{where} ({btype}): columns must be a list of {{key, label}}")
                columns = []
            keys += [c.get("key") for c in columns if isinstance(c, dict)]
            for key in keys:
                if any(key not in item for item in items):
                    errors.append(f"{where} ({btype}): item key {key!r} missing")
        if btype == "actions":
            for aid in data.get("action_ids", []):
                if aid not in allowed_actions:
                    errors.append(f"{where}: action {aid!r} is not allowed")
        if btype == "metric_chart" and data.get("kind") not in ("bar", "line"):
            errors.append(f"{where}: kind must be bar or line")
    return errors


def literal_strings(spec: dict) -> list[str]:
    out = [spec.get("title", "")]
    for block in spec.get("blocks", []):
        data = block.get("data", {}) if isinstance(block, dict) else {}
        out += [v for k, v in data.items() if k in LITERAL_KEYS and isinstance(v, str)]
        cols = data.get("columns") if isinstance(data.get("columns"), list) else []
        out += [c.get("label", "") for c in cols if isinstance(c, dict)]
    return [s for s in out if s]


def payload_numbers(payload: Any) -> set[str]:
    """Every number that appears anywhere in the payload, as digit strings."""
    found: set[str] = set()
    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, (int, float, str)) and not isinstance(v, bool):
            found.update(re.findall(r"\d+", str(v)))
    walk(payload)
    return found


def invented_numbers(spec: dict, payload: dict) -> list[str]:
    """Numbers the model typed into literal text that the payload does not back.

    This is the reliability line: layout may be "good enough", facts may not.
    """
    # TODO(human)
    raise NotImplementedError
