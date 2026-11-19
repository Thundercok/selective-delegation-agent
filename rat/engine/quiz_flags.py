"""Quiz questions the user marked wrong, and the quizzes they came from.

No automatic check told a bad question from a good one (runs 7-8 in
experiments/generative_views/RESULTS.md), so the user's own mark is the measurement. A flag
alone has no denominator, so every quiz shown on the desk is logged too, and the rate is
flagged questions over delivered ones.

    uv run python -m rat.engine.quiz_flags          # rate per document
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List


def quiz_flags_path() -> Path:
    return Path(os.environ.get("RAT_STATE_DIR") or Path.home() / ".rat").expanduser() / "quiz_flags.jsonl"


def _append(record: Dict[str, Any]) -> Path:
    path = quiz_flags_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now()).isoformat(timespec="seconds")


def record_delivered_quiz(card: Dict[str, Any], *, doc_path: str | None = None,
                          now: datetime | None = None) -> Path:
    """One line per quiz shown on the desk. Raises OSError when it cannot be written."""
    questions = card.get("questions") or []
    return _append({
        "kind": "delivered", "at": _stamp(now), "doc": doc_path, "page": card.get("source_page"),
        "generator": card.get("generator"), "count": len(questions),
        "questions": [q.get("question") for q in questions],
    })


def record_flagged_question(card: Dict[str, Any], index: int, *, doc_path: str | None = None,
                            now: datetime | None = None) -> Path:
    """Append the question the user marked wrong. Raises OSError when it cannot be written."""
    q = card["questions"][index]
    return _append({
        "kind": "flagged", "at": _stamp(now), "doc": doc_path,
        "page": q.get("source_page") or card.get("source_page"), "generator": card.get("generator"),
        "question": q.get("question"), "options": q.get("options"),
        "correct_index": q.get("correct_index"), "quote": q.get("quote"),
    })


def flag_rates(path: Path | None = None) -> List[Dict[str, Any]]:
    """Per document: questions delivered, questions flagged, and the share flagged."""
    path = path or quiz_flags_path()
    docs: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue  # a line cut short by a crash should not hide the rest
        row = docs.setdefault(str(rec.get("doc") or "?"), {"delivered": 0, "flagged": set()})
        if rec.get("kind") == "delivered":
            row["delivered"] += int(rec.get("count") or 0)
        else:  # flags written before "kind" existed are flags too
            row["flagged"].add((rec.get("page"), rec.get("question")))
    out = []
    for doc, row in sorted(docs.items()):
        flagged = len(row["flagged"])
        out.append({"doc": doc, "delivered": row["delivered"], "flagged": flagged,
                    "rate": flagged / row["delivered"] if row["delivered"] else None})
    return out


def main() -> int:
    rows = flag_rates()
    if not rows:
        print(f"Chưa có quiz nào trong {quiz_flags_path()}.")
        return 0
    total_d = sum(r["delivered"] for r in rows)
    total_f = sum(r["flagged"] for r in rows)
    for r in rows:
        rate = f"{r['rate']:.0%}" if r["rate"] is not None else "chưa có quiz được ghi"
        print(f"{r['flagged']:>3}/{r['delivered']:<4} {rate:>6}  {Path(r['doc']).name}")
    if total_d:
        print(f"Tổng: {total_f}/{total_d} câu bị đánh dấu sai ({total_f / total_d:.0%}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
