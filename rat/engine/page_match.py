"""Pick the page of an extracted document that best matches a question.

Extracted PDF text carries ``--- Page N ---`` markers (see document_intake/pdf.py).
A question's terms are scored per page by rarity (IDF), so a term that appears on
every page, such as one in the table of contents, counts for little and a rare
term such as "XOR" decides the page.
"""
from __future__ import annotations

import math
import re
import unicodedata

PAGE_MARKER = re.compile(r"--- Page (\d+)(?: \(Scanned OCR\))? ---")

# Question scaffolding that says nothing about where the answer lives.
STOPWORDS = frozenset({
    "cho", "khi", "nào", "thì", "của", "các", "những", "này", "được", "không", "như", "thế",
    "với", "trong", "bài", "một", "gì", "sao", "bao", "nhiêu", "hãy", "giúp", "mình", "tôi",
    "bạn", "có", "và", "ra", "dùng", "làm", "mấy", "đâu", "nêu", "về", "từ", "phần", "đoạn",
    "trang", "tài", "liệu", "tóm", "tắt", "giải", "thích", "là", "hay", "hoặc", "nhau",
    "the", "and", "for", "what", "where", "which", "how", "why", "when", "does", "this",
    "that", "with", "from", "about", "summary", "summarize", "explain", "document", "page",
})


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").lower()


def query_terms(question: str) -> list[str]:
    """Content words of a question, in order, without duplicates."""
    seen: list[str] = []
    for word in re.findall(r"[^\W_]+", _norm(question)):
        if len(word) >= 3 and word not in STOPWORDS and word not in seen:
            seen.append(word)
    return seen


def split_pages(content: str) -> list[tuple[int, int, int]]:
    """(page number, start offset, end offset) for each marked page."""
    marks = list(PAGE_MARKER.finditer(content or ""))
    return [(int(m.group(1)), m.start(), marks[i + 1].start() if i + 1 < len(marks) else len(content))
            for i, m in enumerate(marks)]


def _count(term: str, text: str) -> int:
    return len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def best_page(content: str, terms: list[str]) -> tuple[int, int, int] | None:
    """The page span whose terms are rarest across the document, or None."""
    pages = split_pages(content)
    if not pages or not terms:
        return None
    # Normalize per page: NFC can change length, so offsets stay on the original text.
    counts = [{t: _count(t, _norm(content[start:end])) for t in terms} for _, start, end in pages]
    df = {t: sum(1 for c in counts if c[t]) for t in terms}
    best, best_score = None, None
    for span, c in zip(pages, counts):
        idf = sum(math.log(1 + len(pages) / df[t]) for t in terms if c[t])
        if not idf:
            continue
        # A table of contents names every topic once; it only wins when nothing else matches.
        score = (not _is_contents(content[span[1]:span[2]]), idf, sum(c.values()))
        if best_score is None or score > best_score:  # strict: ties keep the earliest page
            best, best_score = span, score
    return best


def _is_contents(page_text: str) -> bool:
    head = _norm(PAGE_MARKER.sub("", page_text, count=1)).lstrip()
    return bool(re.match(r"(mục lục|table of contents|contents)(?!\w)", head))


def page_window(content: str, terms: list[str], max_chars: int) -> dict | None:
    """A window of at most max_chars that starts on the best page, or None."""
    span = best_page(content, terms)
    if span is None:
        return None
    page, start, end = span
    if end - start > max_chars:
        lowered = _norm(content[start:end])
        hits = [m.start() for t in terms for m in re.finditer(rf"(?<!\w){re.escape(t)}(?!\w)", lowered)]
        if hits:
            start = start + max(0, min(hits) - max_chars // 3)
    return {"page": page, "start": start, "content": content[start:start + max_chars].strip()}
