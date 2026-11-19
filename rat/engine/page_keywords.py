"""Ask the local model for the English words a slide would use, so that a Vietnamese question can be
matched against English slides by page_match (experiments/page_search/RESULTS.md, Sửa 3)."""
from __future__ import annotations

import re

MAX_KEYWORDS = 2


def keyword_messages(question: str) -> list[dict]:
    """Chat messages asking for the slide's own English words for this question."""
    # Examples come from other courses, so they cannot leak answers of the measured questions.
    # Two terms at most: on the 20 tuning questions, a third generic term pulled the page elsewhere.
    system = ("You name the concept a student's question is about, as the English term a lecture slide "
              "title would use. Give the most specific term first, then at most one other exact term. "
              "Never generic words like memory, circuit, data, computer or design. Reply with the "
              "terms only, comma separated.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Hai tiến trình chờ nhau mãi không ai chạy tiếp được gọi là gì?"},
            {"role": "assistant", "content": "deadlock, circular wait"},
            {"role": "user", "content": "Khi hai khoá rơi vào cùng một ô của bảng băm thì xử lý sao?"},
            {"role": "assistant", "content": "hash collision, open addressing"},
            {"role": "user", "content": question}]


def parse_keywords(text: str) -> list[str]:
    """Comma, semicolon or newline separated words from the model's reply, at most MAX_KEYWORDS."""
    parts = [part.strip(" \t.-*\"'`") for part in re.split(r"[,;\n]", text or "")]
    return list(dict.fromkeys(part for part in parts if part))[:MAX_KEYWORDS]


def keyword_query(question: str, model_client, *, timeout: float = 20.0) -> dict:
    """The question plus the model's slide words, or the question alone when the model fails."""
    meta = model_client.chat_with_meta(keyword_messages(question), [], max_tokens=48,
                                       thinking=False, timeout=timeout)
    content = '' if meta.get('error') else (meta.get('message') or {}).get('content') or ''
    keywords = parse_keywords(content)
    return {'query': ' '.join([question, *keywords]), 'keywords': keywords,
            'ms': round(meta.get('duration_ms') or 0.0, 1), 'error': meta.get('error')}
