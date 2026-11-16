"""
rat.kernel.capabilities.quiz — Grounded MCQ quiz generation capability.

Registers:
- generate_quiz: Generates verifiable multiple-choice study questions from supplied text
  or a selected PDF/text file page and saves a `quiz` artifact.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from rat.engine.quiz_generator import generate_quiz_from_text
from rat.kernel.registry import Capability, OperationDefinition


def _read_file_text_for_quiz(file_path: str, page: int) -> tuple[str, int, str]:
    """Read text for quiz generation from a PDF page or plain text file."""
    p = Path(file_path).expanduser().resolve()
    if not p.is_file():
        raise ValueError(f"Tệp nguồn không tồn tại: {file_path}")
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDF không có trang nào.")
        safe_page = max(1, min(total_pages, int(page or 1)))
        text = reader.pages[safe_page - 1].extract_text() or ""
        return text, safe_page, p.name
    text = p.read_text(encoding="utf-8", errors="replace")
    return text, int(page or 0), p.name


def create_quiz_capability(db: Any = None) -> Capability:
    """Create and configure RAT's interactive quiz generation capability."""
    del db
    cap = Capability(
        name="quiz",
        title="Trắc nghiệm ôn tập",
        description="Tạo bộ câu hỏi trắc nghiệm 4 lựa chọn có trích nguồn từ tài liệu hoặc trang PDF.",
    )

    def handle_generate_quiz(args: Dict[str, Any], **context) -> Dict[str, Any]:
        raw_text = str(args.get("source_text") or "").strip()
        file_path = str(args.get("file_path") or context.get("selected_document_path") or "").strip()
        try:
            page = int(args.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        try:
            count = int(args.get("count") or 5)
        except (TypeError, ValueError):
            count = 5

        title = str(args.get("title") or "").strip()
        doc_name = ""
        source_page = page if raw_text and args.get("page") else 0

        if not raw_text and file_path:
            try:
                raw_text, source_page, doc_name = _read_file_text_for_quiz(file_path, page)
            except Exception as exc:
                return {"found": False, "error": str(exc)}

        if not raw_text:
            return {
                "found": False,
                "error": "Cần cung cấp đoạn văn bản nguồn hoặc đường dẫn tệp PDF để tạo trắc nghiệm.",
            }

        resolved_title = title or (
            f"Trắc nghiệm · {doc_name}" + (f" (Trang {source_page})" if source_page else "")
            if doc_name
            else "Trắc nghiệm ôn tập"
        )

        result = generate_quiz_from_text(
            raw_text,
            title=resolved_title,
            count=count,
            source_page=source_page,
        )
        if not result.get("questions"):
            return {
                "found": False,
                "error": "Đoạn nội dung quá ngắn hoặc chưa đủ dữ kiện để tạo câu hỏi trắc nghiệm.",
            }
        return {**result, "found": True}

    op = OperationDefinition(
        name="generate_quiz",
        description=(
            "Generate grounded multiple-choice study questions from provided source_text or a local PDF/text file_path. "
            "Returns interactive quiz questions with options, verified correct_index, and source quotes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "source_text": {
                    "type": "string",
                    "description": "Verbatim source passage or study notes to create questions from.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional path to a PDF or text file to extract a page from.",
                },
                "page": {
                    "type": "integer",
                    "description": "1-based PDF page number to read when using file_path (default 1).",
                    "default": 1,
                },
                "title": {
                    "type": "string",
                    "description": "Optional quiz card title.",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of multiple-choice questions to generate (1-10, default 5).",
                    "default": 5,
                },
            },
        },
        handler=handle_generate_quiz,
        artifact_kind="quiz",
        present_result=True,
    )
    cap.register_operation(op)
    return cap
