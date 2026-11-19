"""Save an answer the user asked to keep as a Markdown file on disk.

The desk only says a note was saved after the file is written and read back,
so "đã lưu" is never a claim the app cannot prove.
"""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
from typing import Any, Iterable


def notes_dir() -> Path:
    """Where notes go: RAT_NOTES_DIR, else the test/state dir, else a visible Documents folder."""
    if os.environ.get("RAT_NOTES_DIR"):
        return Path(os.environ["RAT_NOTES_DIR"]).expanduser()
    if os.environ.get("RAT_STATE_DIR"):
        return Path(os.environ["RAT_STATE_DIR"]).expanduser() / "notes"
    return Path.home() / "Documents" / "Ghi chú của Chuột"


def _slug(text: str, limit: int = 60) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", text).strip(" .")
    return re.sub(r"\s+", " ", cleaned)[:limit].rstrip(" .") or "Ghi chú"


def _cited(sources: Iterable[Any]) -> dict | None:
    for source in sources or []:
        if isinstance(source, dict) and (source.get("path") or source.get("file_path")):
            return source
    return None


def _quiz_lines(quiz: dict) -> list[str]:
    lines = [f"## {quiz.get('title') or 'Trắc nghiệm'}", ""]
    if quiz.get("instruction"):
        lines += [f"_{quiz['instruction']}_", ""]
    questions = quiz.get("questions") or []
    kept = [item for item in questions if not item.get("flagged")]
    for n, item in enumerate(kept, 1):
        lines.append(f"{n}. {item.get('question', '').strip()}")
        for i, option in enumerate(item.get("options") or []):
            mark = " ✓" if i == item.get("correct_index") else ""
            lines.append(f"   - {option}{mark}")
        if item.get("quote"):
            lines.append(f"   > {str(item['quote']).strip()}")
        lines.append("")
    if len(kept) < len(questions):
        lines += [f"_Đã bỏ {len(questions) - len(kept)} câu bạn đánh dấu sai._", ""]
    return lines


def note_markdown(question: str, answer: str, sources: Iterable[Any], saved_at: datetime,
                  quiz: dict | None = None) -> str:
    if quiz and quiz.get("questions"):
        # The answer of a quiz turn is only a receipt; the questions are what is worth keeping.
        lines = [f"# {question.strip() or 'Trắc nghiệm'}", "", *_quiz_lines(quiz)]
    else:
        lines = [f"# {question.strip() or 'Ghi chú'}", "", answer.strip(), ""]
    source = _cited(sources)
    if source:
        path = Path(source.get("path") or source.get("file_path"))
        page = source.get("page")
        where = f"{path.name} · trang {page}" if type(page) is int and page >= 1 else path.name
        lines += [f"Nguồn: {where}", ""]
        excerpt = str(source.get("excerpt") or "").strip()
        if excerpt:
            lines += ["> " + line for line in excerpt[:600].splitlines() if line.strip()] + [""]
    lines.append(f"Lưu lúc {saved_at:%Y-%m-%d %H:%M}")
    return "\n".join(lines) + "\n"


def save_answer_note(question: str, answer: str, sources: Iterable[Any] = (),
                     *, now: datetime | None = None, folder: Path | None = None,
                     quiz: dict | None = None) -> Path:
    """Write the note and return its path; raises OSError when it cannot be written and verified."""
    saved_at = now or datetime.now()
    folder = folder or notes_dir()
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{saved_at:%Y-%m-%d %H%M} - {_slug(question)}"
    path = folder / f"{stem}.md"
    n = 2
    while path.exists():
        path = folder / f"{stem} ({n}).md"
        n += 1
    text = note_markdown(question, answer, sources, saved_at, quiz)
    path.write_text(text, encoding="utf-8")
    if path.read_text(encoding="utf-8") != text:
        raise OSError(f"note_not_verified: {path}")
    return path
