"""
rat.engine.quiz_generator — Causal-schema grounded quiz generation and deterministic fallback.

Orders schema fields alphabetically (`a_quote` -> `b_question` -> `c_correct` -> `d_distractors`)
so constrained JSON decoders emit the verbatim quote and question before writing the correct answer
and 3 distractors. Python code then verifies uniqueness and grounding, shuffles the distractors
deterministically, and rotates `correct_index` through A-D across the set.
"""
from __future__ import annotations

import json
import os
import random
import re
from typing import Any, Dict, List
import unicodedata

from rat.engine.page_match import STOPWORDS

# A special case can also be true ("XNOR ra 1 khi cả hai đầu vào bằng 1"); a 4B model cannot be
# prompted out of offering one (experiments/generative_views/RESULTS.md, run 5), so the quiz
# says which option counts: the one that states the whole rule.
QUIZ_INSTRUCTION = "Chọn phát biểu đúng và đầy đủ nhất."

# A key in words must share at least this many content words with its quote. Runs 4-5 (60
# questions): the ill-posed ones, whose quote was a table header, shared 0-1; the rest shared 3+.
MIN_KEY_QUOTE_WORDS = 2


QUIZ_GENERATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["a_quote", "b_question", "c_correct", "d_distractors"],
                "properties": {
                    "a_quote": {"type": "string"},
                    "b_question": {"type": "string"},
                    "c_correct": {"type": "string"},
                    "d_distractors": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                },
            },
        }
    },
}

_CHOICE_PREFIX_RE = re.compile(r"^\s*[A-Da-d]\s*[.):\-]\s*")


def strip_choice_prefix(text: str) -> str:
    """Strip leading option labels like 'A. ' or 'B) ' from a choice string."""
    return _CHOICE_PREFIX_RE.sub("", str(text or "").strip()).strip()


def _normalize_for_grounding(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (text or "").lower())).strip()


def is_quote_grounded(quote: str, source_text: str) -> bool:
    """Check whether `quote` matches content in `source_text` via substring or word overlap."""
    clean_source = _normalize_for_grounding(source_text)
    if not clean_source:
        return True
    clean_quote = _normalize_for_grounding(quote)
    if not clean_quote:
        return False
    if clean_quote in clean_source:
        return True
    if len(clean_quote) >= 15:
        for start in range(0, len(clean_quote) - 14, 5):
            if clean_quote[start : start + 15] in clean_source:
                return True
    words = [w for w in clean_quote.split() if len(w) >= 3]
    if not words:
        return False
    src_words = set(clean_source.split())
    hits = sum(1 for w in words if w in src_words)
    return (hits / len(words)) >= 0.6


def _content_words(text: str) -> set:
    lowered = unicodedata.normalize("NFC", str(text or "")).lower()
    return {w for w in re.findall(r"[^\W\d_]+", lowered) if len(w) >= 2 and w not in STOPWORDS}


def key_supported_by_quote(correct: str, quote: str) -> bool:
    """Whether the quote states the answer, not only sits on the same page."""
    key_words = _content_words(correct)
    if not key_words:
        # A value such as "0" for NAND(1, 1): its options are other values, so only one can be true.
        numbers = re.findall(r"\d+", str(correct or ""))
        return bool(numbers) and all(re.search(rf"(?<!\d){n}(?!\d)", str(quote or "")) for n in numbers)
    return len(key_words & _content_words(quote)) >= MIN_KEY_QUOTE_WORDS


def compile_quiz_items(
    raw_items: List[Dict[str, Any]],
    source_text: str = "",
    source_page: int = 0,
    max_count: int = 5,
) -> List[Dict[str, Any]]:
    """Validate, deduplicate, deterministically shuffle, and ground-check raw quiz items."""
    compiled: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_items or []):
        if not isinstance(item, dict):
            continue
        question = str(item.get("b_question") or item.get("question") or "").strip()
        correct = strip_choice_prefix(item.get("c_correct") or item.get("correct") or "")
        raw_distractors = item.get("d_distractors") or item.get("distractors") or []
        if not question or not correct or not isinstance(raw_distractors, list):
            continue

        seen = {correct.lower()}
        distractors: List[str] = []
        for d in raw_distractors:
            clean_d = strip_choice_prefix(str(d))
            if clean_d and clean_d.lower() not in seen:
                seen.add(clean_d.lower())
                distractors.append(clean_d)
        if len(distractors) < 3:
            continue
        quote = str(item.get("a_quote") or item.get("quote") or "").strip()
        if quote and not key_supported_by_quote(correct, quote):
            continue

        choices_raw = list(distractors[:3])
        rng = random.Random(f"{idx}:{question}")
        rng.shuffle(choices_raw)
        # Rotate the answer through A-D across the set so its position carries no pattern;
        # the start letter is seeded so every quiz does not open with A.
        if not compiled:
            rotation = random.Random(question).randrange(4)
        correct_index = (rotation + len(compiled)) % 4
        choices_raw.insert(correct_index, correct)
        options = [f"{'ABCD'[i]}. {c}" for i, c in enumerate(choices_raw)]

        grounded = is_quote_grounded(quote or correct, source_text)
        try:
            item_page = int(item.get("source_page") or source_page or 0)
        except (TypeError, ValueError):
            item_page = int(source_page or 0)

        compiled.append(
            {
                "question": question,
                "options": options,
                "correct_index": correct_index,
                "quote": quote,
                "source_page": item_page,
                "grounded": grounded,
            }
        )
        if len(compiled) >= max_count:
            break
    return compiled


def _split_factual_statements(source_text: str) -> List[str]:
    """Extract clean informative statements (>= 25 chars) from source text."""
    raw_segments = re.split(r"(?<=[.!?])\s+|\n+", str(source_text or "").strip())
    statements: List[str] = []
    seen = set()
    for seg in raw_segments:
        clean = re.sub(r"\s+", " ", seg).strip(" -•*\t\r\n")
        if len(clean) >= 25 and clean.lower() not in seen:
            seen.add(clean.lower())
            statements.append(clean)
    return statements


def _make_stem_from_statement(stmt: str, idx: int) -> tuple[str, str]:
    """Turn a factual statement into (question_stem, topic_label)."""
    split_match = re.match(
        r"^(.{3,45}?)\s+(?:là|gồm|cho|có|=|:)\s+(.+)$",
        stmt,
        flags=re.IGNORECASE,
    )
    if split_match:
        subject = split_match.group(1).strip(" :-")
        return f"Theo tài liệu, nhận định nào sau đây đúng về {subject}?", subject
    words = stmt.split()[:6]
    hint = " ".join(words).rstrip(".,;:")
    return f"Câu {idx + 1}: Nội dung nào sau đây phù hợp với tài liệu (\"{hint}…\")?", hint


QUIZ_MODEL_TIMEOUT_S = 240.0


def extract_fallback_quiz(
    source_text: str,
    count: int = 5,
    source_page: int = 0,
) -> List[Dict[str, Any]]:
    """Deterministically build verifiable MCQ items from source statements without an LLM."""
    statements = _split_factual_statements(source_text)
    if not statements:
        return []

    generic_foils = [
        "Không phụ thuộc vào bất kỳ điều kiện hay trạng thái đầu vào nào.",
        "Chỉ áp dụng khi tất cả tín hiệu điều khiển bị vô hiệu hóa hoàn toàn.",
        "Luôn trả về giá trị ngược lại so với quy tắc chuẩn của hệ thống.",
        "Chỉ có thể hoạt động tuần tự khi ngắt toàn bộ bộ nhớ đệm.",
        "Tài liệu khẳng định trường hợp này không tồn tại trong thực tế.",
    ]

    raw_items: List[Dict[str, Any]] = []
    for idx, stmt in enumerate(statements[: max(1, count)]):
        stem, _topic = _make_stem_from_statement(stmt, idx)
        other_stmts = [s for j, s in enumerate(statements) if j != idx]
        distractors: List[str] = []
        for s in other_stmts:
            if len(distractors) >= 3:
                break
            distractors.append(s)
        for foil in generic_foils:
            if len(distractors) >= 3:
                break
            if foil.lower() != stmt.lower() and foil not in distractors:
                distractors.append(foil)
        raw_items.append(
            {
                "a_quote": stmt,
                "b_question": stem,
                "c_correct": stmt,
                "d_distractors": distractors[:3],
                "source_page": source_page,
            }
        )

    return compile_quiz_items(
        raw_items,
        source_text=source_text,
        source_page=source_page,
        max_count=count,
    )


def generate_quiz_from_text(
    source_text: str,
    *,
    title: str = "Trắc nghiệm ôn tập",
    count: int = 5,
    source_page: int = 0,
    model_client: Any = None,
) -> Dict[str, Any]:
    """Generate a verified interactive quiz payload from source text with deterministic fallback."""
    try:
        n_questions = max(1, min(10, int(count or 5)))
    except (TypeError, ValueError):
        n_questions = 5

    clean_text = str(source_text or "").strip()
    questions: List[Dict[str, Any]] = []
    model_error = "model_unavailable"

    client = model_client
    if client is None and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from rat.engine.slm import assistant_engine
            candidate = assistant_engine()
            if getattr(candidate, "is_service_running", lambda: False)():
                client = candidate
        except Exception:
            client = None

    if client is not None and clean_text:
        # One spare: the model writes a question on the table header in every run so far, and
        # key_supported_by_quote drops it; max_count below still caps the quiz at n_questions.
        n_asked = n_questions + 1
        system_msg = (
            "Bạn là trợ giảng soạn câu hỏi trắc nghiệm CHỈ dựa trên đoạn tài liệu được cung cấp. "
            "Với mỗi câu, trước tiên hãy trích nguyên văn một câu/đoạn từ tài liệu vào `a_quote`, "
            "sau đó đặt câu hỏi tiếng Việt vào `b_question`, viết đáp án đúng vào `c_correct`, "
            "và viết đúng 3 phương án nhiễu sai vào `d_distractors` (không lặp lại đáp án đúng, không thêm A/B/C/D)."
        )
        user_msg = (
            f"Trang {source_page or 1}:\n{clean_text[:7000]}\n\n"
            f"Hãy tạo đúng {n_asked} câu trắc nghiệm tiếng Việt bằng JSON đúng schema."
        )
        try:
            # Measured on qwen3:4b-instruct: ~490 output tokens and 64-90 s for five questions
            # on one page, so the 90 s chat default times out on longer pages.
            meta = client.chat_with_meta(
                [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                [],
                response_format=QUIZ_GENERATION_SCHEMA,
                max_tokens=400 * n_asked,
                timeout=QUIZ_MODEL_TIMEOUT_S,
            )
            model_error = (meta or {}).get("error") or ""
            raw_content = (meta or {}).get("message", {}).get("content", "")
            parsed = json.loads(raw_content) if isinstance(raw_content, str) and raw_content.strip() else {}
            if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
                questions = compile_quiz_items(
                    parsed["items"],
                    source_text=clean_text,
                    source_page=source_page,
                    max_count=n_questions,
                )
                if not questions:
                    model_error = "no_grounded_items"
            else:
                model_error = model_error or "invalid_model_output"
        except Exception as exc:
            questions = []
            model_error = f"model_call_failed: {exc}"

    generator = "model" if questions else "extract"
    if not questions and clean_text:
        questions = extract_fallback_quiz(clean_text, count=n_questions, source_page=source_page)

    return {
        "visual_type": "quiz",
        "title": title,
        "instruction": QUIZ_INSTRUCTION,
        "source_page": source_page,
        "questions": questions,
        "question_count": len(questions),
        "grounded_count": sum(1 for q in questions if q.get("grounded")),
        # "extract" means the questions were lifted from source sentences, not written by a model.
        "generator": generator,
        "model_error": None if generator == "model" else model_error,
    }
