"""The fill-in-the-blank quiz fallback, kept here as the experiment that removed it from RAT.

Two rounds, 6/20 then 10/20 bad (see RESULTS.md); both hit the KILL line, so RAT no longer has a
quiz without a model. cloze_probe.py rebuilds both rounds from this file.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from rat.engine.page_match import STOPWORDS
from rat.engine.quiz_generator import _normalize_for_grounding, compile_quiz_items


def _split_factual_statements(source_text: str) -> List[str]:
    """Extract clean informative statements (>= 25 chars) from source text."""
    # PDF text breaks lines mid-sentence ("Ví dụ tranh có\ncopier mà …"). Join a break that
    # follows a comma or slash, or that a lowercase word continues; keep the others, which end
    # headings and table rows.
    lines = [line.strip() for line in str(source_text or "").strip().splitlines()]
    joined = lines[0] if lines else ""
    for line in lines[1:]:
        continues = joined[-1:] in ",;/(–-" or line[:1].islower()
        joined += (" " if continues and joined and line else "\n") + line
    raw_segments = re.split(r"(?<=[.!?])\s+|\n+", joined)
    statements: List[str] = []
    seen = set()
    for seg in raw_segments:
        clean = re.sub(r"\s+", " ", seg).strip(" -•*\t\r\n")
        if len(clean) >= 25 and clean.lower() not in seen:
            seen.add(clean.lower())
            statements.append(clean)
    return statements



# The fallback asks for one word, so the "đầy đủ nhất" rule does not apply to it.
CLOZE_INSTRUCTION = "Chọn từ điền vào chỗ trống để được đúng câu trong tài liệu."

_TOKEN_RE = re.compile(r"[^\W_]+")
_KIND_ORDER = {"num": 0, "caps": 1, "ident": 2, "word": 3}


# A Vietnamese syllable written without marks ("tham", "tranh", "trong") passes isascii(); its
# shape gives it away. Some English words fit the shape too ("main"); losing them costs a blank,
# not a wrong question.
_VI_SYLLABLE_RE = re.compile(
    r"(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdghklmnprstvx])?[aeiouy]{1,3}(ng|nh|ch|[cmnptiyou])?"
)


def _term_kind(token: str) -> str | None:
    """What a blank can hold: a number, an acronym, an identifier, or a Latin-script word."""
    # isdecimal, not isdigit: "①" and "²" are digits that int() rejects.
    if token.isdecimal():
        return "num"
    if len(token) < 2:
        return None
    vietnamese = not token.isascii() or bool(_VI_SYLLABLE_RE.fullmatch(token.lower()))
    if token.isupper() and any(c.isalpha() for c in token):
        # "KHÔNG", "TRƯỚC" are words in capitals, not acronyms such as "XOR" or "GDP".
        return None if vietnamese else "caps"
    if any(c.isdigit() or c in "²³" for c in token) or any(c.isupper() for c in token[1:]):
        return "ident"
    # Vietnamese syllables make poor blanks ("đồng", "thuộc"); English terms such as "placed" do not.
    if not vietnamese and token.isalpha() and len(token) >= 4 and token.lower() not in STOPWORDS:
        return "word"
    return None


def _number_distractors(answer: str, pool: List[str]) -> List[str]:
    same_width = [n for n in pool if len(n) == len(answer)]
    picks = sorted(same_width, key=lambda n: abs(int(n) - int(answer)))
    step = 1
    while len(picks) < 6 and step < 50:
        for cand in (int(answer) + step, int(answer) - step):
            text = str(cand)
            if cand >= 0 and len(text) == len(answer) and text not in picks:
                picks.append(text)
        step += 1
    return picks


def _in_comma_list(stmt: str, match: re.Match) -> bool:
    """A term that is one short item of a list: the other items are just as true in its place."""
    if stmt.count(",") < 2:
        return False
    # The first item carries the lead-in ("KHÔNG đổi tên file, tên hàm, …"), so also count a term
    # that touches a comma.
    if stmt[match.end():].lstrip()[:1] == "," or stmt[: match.start()].rstrip()[-1:] == ",":
        return True
    start = max(stmt.rfind(",", 0, match.start()), stmt.rfind(":", 0, match.start())) + 1
    ends = [i for i in (stmt.find(",", match.end()), stmt.find(".", match.end())) if i >= 0]
    segment = stmt[start: min(ends) if ends else len(stmt)]
    return len(_TOKEN_RE.findall(segment)) <= 3


def _is_page_furniture(stmt: str, match: re.Match, tokens: List[re.Match]) -> bool:
    """A citation mark "[11]", or a number in a row of numbers such as a table header."""
    if stmt[match.start() - 1: match.start()] == "[" and stmt[match.end(): match.end() + 1] == "]":
        return True
    if match.group(0).isdecimal():
        numeric = sum(1 for m in tokens if m.group(0).isdecimal())
        return numeric * 5 >= len(tokens) * 2
    return False


def _cloze_item(stmt: str, tokens: List[re.Match], source_norm: str,
                pool: Dict[str, List[str]], freq: Dict[str, int]) -> Dict[str, Any] | None:
    in_stmt = {m.group(0).lower() for m in tokens}
    candidates = [m for m in tokens if _term_kind(m.group(0))
                  and not _in_comma_list(stmt, m) and not _is_page_furniture(stmt, m, tokens)]
    # The rarest term on the page decides what the sentence is about.
    candidates.sort(key=lambda m: (freq[m.group(0).lower()], _KIND_ORDER[_term_kind(m.group(0))], -len(m.group(0))))
    for match in candidates:
        answer, kind = match.group(0), _term_kind(match.group(0))
        others = [w for w in pool[kind] if w.lower() not in in_stmt]
        if kind == "num":
            others = _number_distractors(answer, others)
        distractors: List[str] = []
        for cand in others:
            filled = stmt[: match.start()] + cand + stmt[match.end():]
            # One right answer by construction: no distractor may rebuild a sentence the page has.
            if _normalize_for_grounding(filled) not in source_norm and cand.lower() != answer.lower():
                distractors.append(cand)
            if len(distractors) == 3:
                break
        if len(distractors) < 3:
            continue
        left, right = stmt[: match.start()], stmt[match.end():]
        if len(left) > 110:
            left = "…" + left[-100:].lstrip()
        if len(right) > 110:
            right = right[:100].rstrip() + "…"
        return {
            "a_quote": stmt,
            "b_question": f"Điền vào chỗ trống: “{left}____{right}”",
            "c_correct": answer,
            "d_distractors": distractors,
        }
    return None


def extract_fallback_quiz(
    source_text: str,
    count: int = 5,
    source_page: int = 0,
) -> List[Dict[str, Any]]:
    """Fill-in-the-blank questions from page sentences, built and checked in code without a model."""
    statements = _split_factual_statements(source_text)
    if not statements:
        return []
    source_norm = _normalize_for_grounding(source_text)
    tokenized = [(stmt, list(_TOKEN_RE.finditer(stmt))) for stmt in statements]
    freq: Dict[str, int] = {}
    pool: Dict[str, List[str]] = {kind: [] for kind in _KIND_ORDER}
    seen_terms: set = set()
    for _stmt, tokens in tokenized:
        for m in tokens:
            word = m.group(0)
            freq[word.lower()] = freq.get(word.lower(), 0) + 1
            kind = _term_kind(word)
            if kind and word.lower() not in seen_terms:
                seen_terms.add(word.lower())
                pool[kind].append(word)

    raw_items: List[Dict[str, Any]] = []
    for stmt, tokens in tokenized:
        item = _cloze_item(stmt, tokens, source_norm, pool, freq)
        if item:
            item["source_page"] = source_page
            raw_items.append(item)
        if len(raw_items) >= count:
            break

    return compile_quiz_items(
        raw_items,
        source_text=source_text,
        source_page=source_page,
        max_count=count,
    )
