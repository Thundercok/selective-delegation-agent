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
    "slide", "slides", "nằm", "nói", "chương", "chapter", "mục", "section", "tệp",
    "the", "and", "for", "what", "where", "which", "how", "why", "when", "does", "this",
    "that", "with", "from", "about", "summary", "summarize", "explain", "document", "page",
})


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").lower()


def query_terms(question: str) -> list[str]:
    """Content words of a question, in order, without duplicates."""
    seen: list[str] = []
    for m in re.finditer(r"[a-z0-9à-ỹ]+(?:-[a-z0-9à-ỹ]+)+|[^\W_]+", _norm(question)):
        word = m.group(0)
        if "-" in word:
            if word not in STOPWORDS and word not in seen:
                seen.append(word)
            for part in word.split("-"):
                if len(part) >= 3 and part not in STOPWORDS and part not in seen:
                    seen.append(part)
        elif (len(word) >= 3 or (len(word) == 2 and word.isdigit())) and word not in STOPWORDS and word not in seen:
            seen.append(word)
    return seen


def split_pages(content: str) -> list[tuple[int, int, int]]:
    """(page number, start offset, end offset) for each marked page."""
    marks = list(PAGE_MARKER.finditer(content or ""))
    return [(int(m.group(1)), m.start(), marks[i + 1].start() if i + 1 < len(marks) else len(content))
            for i, m in enumerate(marks)]


def _count(term: str, text: str) -> int:
    if " " in term:
        parts = [rf"{re.escape(w)}(?:es|s)?" for w in term.split()]
        pat = r"(?:[\s\'-]+|)".join(parts)
        return len(re.findall(rf"(?<!\w){pat}(?!\w)", text))
    if "-" in term:
        return len(re.findall(rf"(?<![\w-]){re.escape(term)}(?:es|s)?(?![\w-])", text))
    if len(term) >= 5 and term.isascii():
        return len(re.findall(rf"(?:(?<!\w)|(?<=de)){re.escape(term)}(?:es|s)?(?!\w)", text))
    return len(re.findall(rf"(?<!\w){re.escape(term)}(?:es|s)?(?!\w)", text))


def _head_text(page_text: str) -> str:
    """First two non-bullet lines of a page (running title and slide/section heading)."""
    lines = [
        ln.strip()
        for ln in PAGE_MARKER.sub("", page_text, count=1).splitlines()
        if ln.strip() and not ln.lstrip().startswith(("•", "-", "*"))
    ]
    return _norm(" ".join(lines[:2]))


def has_specific_lexical_match(content: str, terms: list[str]) -> bool:
    """True when the question already shares at least one rare or two distinct terms with the document."""
    pages = split_pages(content)
    if not pages or not terms:
        return False
    page_texts = [_norm(content[start:end]) for _, start, end in pages]
    df = {t: sum(1 for pt in page_texts if _count(t, pt)) for t in terms}
    specific = [t for t in terms if 0 < df.get(t, 0) <= max(3, len(pages) // 2)]
    return len(specific) >= 2 or (len(specific) == 1 and df[specific[0]] <= 6)


_SLM_KEYWORD_CACHE: dict[str, list[str]] = {}
_PHRASE_STOP = frozenset({"of", "to", "in", "the", "and", "for", "law", "rule", "unit"})


def _terms_from_keywords(keywords: list[str]) -> list[str]:
    phrases: list[str] = []
    for k in keywords[:3]:
        raw_words = [
            w for w in re.findall(r"[a-z0-9]+", k.lower())
            if len(w) >= 2 and w not in _PHRASE_STOP
        ]
        if len(raw_words) >= 2:
            phrases.append(" ".join(raw_words))
    words = [w for w in query_terms(" ".join(keywords)) if w not in _PHRASE_STOP and w.isascii()]
    return list(dict.fromkeys(phrases + words))


def translate_query_terms_slm(question: str, model_client=None) -> list[str]:
    """Use rat.engine.page_keywords to map a Vietnamese paraphrase to English slide phrases and terms."""
    key = _norm(question).strip()
    if not key:
        return []
    if key in _SLM_KEYWORD_CACHE:
        return list(_SLM_KEYWORD_CACHE[key])
    try:
        from rat.engine.page_keywords import keyword_query
        if model_client is None:
            from rat.config import config
            from rat.engine.slm import SLMEngine
            model_client = SLMEngine(model="qwen3:4b-instruct", ollama_url=config.ollama_url)
        res = keyword_query(question, model_client)
        terms = _terms_from_keywords(res.get("keywords") or [])
        if terms:
            _SLM_KEYWORD_CACHE[key] = terms
        return terms
    except Exception:
        return []


def best_page(
    content: str,
    terms: list[str],
    *,
    question: str | None = None,
    slm_fallback: bool = False,
    model_client=None,
) -> tuple[int, int, int] | None:
    """The page span whose terms are rarest across the document, or None."""
    pages = split_pages(content)
    if not pages:
        return None
    used_slm = False
    if slm_fallback and question and not has_specific_lexical_match(content, terms):
        en_terms = translate_query_terms_slm(question, model_client=model_client)
        if en_terms:
            terms = en_terms
            used_slm = True
    if not terms:
        return None
    # Normalize per page: NFC can change length, so offsets stay on the original text.
    page_texts = [content[start:end] for _, start, end in pages]
    counts = [{t: _count(t, _norm(pt)) for t in terms} for pt in page_texts]
    df = {t: sum(1 for c in counts if c[t]) for t in terms}
    head_counts = [{t: _count(t, _head_text(pt)) for t in terms} for pt in page_texts]

    def _valid(t: str) -> bool:
        d = df.get(t, 0)
        if d <= 0:
            return False
        if not used_slm:
            return True
        if " " in t:
            return d <= max(4, len(pages) // 2)
        return d <= max(3, len(pages) // 4)

    best, best_score = None, None
    for span, c, hc, pt in zip(pages, counts, head_counts, page_texts):
        idf = sum((2.5 if " " in t else 1.0) * math.log(1 + len(pages) / df[t]) for t in terms if c[t] and _valid(t))
        if not idf:
            continue
        head_idf = sum((2.5 if " " in t else 1.0) * math.log(1 + len(pages) / df[t]) for t in terms if hc[t] and _valid(t))
        # A table of contents names every topic once; it only wins when nothing else matches.
        # Ties on total IDF break by heading IDF, then earliest page (where the concept is introduced).
        primary = round(idf + head_idf, 6) if used_slm else round(idf, 6)
        score = (not _is_contents(pt), primary, round(head_idf, 6), -span[0])
        if best_score is None or score > best_score:
            best, best_score = span, score
    return best


def _is_contents(page_text: str) -> bool:
    head = _norm(PAGE_MARKER.sub("", page_text, count=1)).lstrip()
    return bool(re.match(r"(mục lục|table of contents|contents)(?!\w)", head))


def page_window(
    content: str,
    terms: list[str],
    max_chars: int,
    *,
    question: str | None = None,
    slm_fallback: bool = False,
    model_client=None,
) -> dict | None:
    """A window of at most max_chars that starts on the best page, or None."""
    span = best_page(content, terms, question=question, slm_fallback=slm_fallback, model_client=model_client)
    if span is None:
        return None
    page, start, end = span
    if end - start > max_chars:
        lowered = _norm(content[start:end])
        hits = [m.start() for t in terms for m in re.finditer(rf"(?<!\w){re.escape(t)}(?!\w)", lowered)]
        if hits:
            start = start + max(0, min(hits) - max_chars // 3)
    return {"page": page, "start": start, "content": content[start:start + max_chars].strip()}
