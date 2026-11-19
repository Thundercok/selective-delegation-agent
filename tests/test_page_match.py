"""Page choice for a question over page-marked document text."""
import json

from rat.engine.page_match import best_page, page_window, query_terms
from rat.engine.selected_document_qa import answer_selected_document, MAX_READ_CHARS
from tests.test_selected_document_qa import env  # noqa: F401  (fixture)

PAGES = {
    1: "Mục lục. 1 Hệ đếm. 2 Cổng logic: AND, OR, XOR. 3 Bìa Karnaugh.",
    2: "Hệ đếm nhị phân. Đổi số thập phân sang nhị phân bằng cách chia 2. " * 60,
    3: "Cổng logic. Cổng XOR ra 1 khi hai đầu vào khác nhau. Cổng AND ra 1 khi cả hai bằng 1.",
    4: "Rút gọn bằng bìa Karnaugh: hai ô kề nhau chỉ khác một biến. Cổng nào cũng được vẽ lại.",
}
TEXT = "\n".join(f"--- Page {n} ---\n{body}" for n, body in PAGES.items())


def test_terms_keep_short_rare_words_and_drop_scaffolding():
    assert query_terms("Cổng XOR cho ra 1 khi nào?") == ["cổng", "xor"]
    assert query_terms("Tóm tắt tài liệu này") == []


def test_rare_term_beats_table_of_contents():
    # Page 1 is a table of contents that names both topics once; it must not win the tie.
    assert best_page(TEXT, query_terms("Cổng XOR cho ra 1 khi nào?"))[0] == 3
    assert best_page(TEXT, query_terms("Bìa Karnaugh dùng để làm gì?"))[0] == 4


def test_heading_intro_beats_later_page_that_repeats_terms_more_often():
    deck = "\n".join([
        "--- Page 9 ---\nCS2100 Combinational Circuits 9\nGATE-LEVEL DESIGN: HALF ADDER\n• Example: Build a Half Adder.",
        "--- Page 15 ---\nCS2100 Combinational Circuits 15\nGATE-LEVEL DESIGN: FULL ADDER\n• Full Adder made from two Half Adders.\nHalf Adder 1 and Half Adder 2 and Half Adder carry.",
    ])
    assert best_page(deck, query_terms("Thiết kế half adder nằm ở slide nào?"))[0] == 9


def test_hyphenated_compound_terms_and_two_digit_numbers_are_preserved():
    assert "i-format" in query_terms("I-format chia 32 bit của lệnh thành những trường nào?")
    assert "32" in query_terms("I-format chia 32 bit của lệnh thành những trường nào?")
    assert "j-k" in query_terms("J-K flip-flop chuyển sang trạng thái toggle khi nào?")


def test_slm_fallback_translates_paraphrase_only_when_lexical_match_is_absent(monkeypatch):
    import rat.engine.page_match as pm

    deck = "\n".join([
        "--- Page 1 ---\nTitle Slide",
        "--- Page 8 ---\nMEMORY: WORD ALIGNMENT\n• Words are aligned in memory if they begin at a byte address.",
        "--- Page 12 ---\nInstruction Fetch",
    ])
    calls = []

    def fake_translate(q, model_client=None):
        calls.append(q)
        return ["word", "alignment", "byte", "address"]

    monkeypatch.setattr(pm, "translate_query_terms_slm", fake_translate)

    # Strong lexical match does NOT call SLM
    assert best_page(deck, query_terms("Word alignment nằm ở slide nào?"), question="Word alignment nằm ở slide nào?", slm_fallback=True)[0] == 8
    assert calls == []

    # Paraphrase with no shared technical terms triggers SLM keyword translation
    q_vi = "Quy định một từ phải bắt đầu ở địa chỉ chia hết cho số cái của nó nằm ở slide nào?"
    assert best_page(deck, query_terms(q_vi), question=q_vi, slm_fallback=True)[0] == 8
    assert calls == [q_vi]


def test_no_markers_or_no_hits_give_no_page():
    assert best_page("plain text without markers", ["xor"]) is None
    assert best_page(TEXT, ["flipflop"]) is None


def test_window_starts_on_the_page_and_respects_the_limit():
    window = page_window(TEXT, ["xor"], 200)
    assert window["page"] == 3 and window["content"].startswith("--- Page 3 ---")
    assert len(window["content"]) <= 200


def test_truncated_read_answers_from_the_matching_page(env):  # noqa: F811
    runtime, path, client = env
    path.write_text(TEXT)
    runtime.db.upsert_document({'file_path': str(path), 'file_name': path.name, 'file_ext': '.txt',
        'file_size': path.stat().st_size, 'created_at': 1, 'modified_at': 2, 'indexed_at': 2,
        'content_text': TEXT})
    assert len(TEXT) > MAX_READ_CHARS
    response = answer_selected_document(runtime, 'Cổng XOR cho ra 1 khi nào?', str(path), model_client=client)
    assert response.error is None
    assert [s.tool_name for s in response.steps if s.tool_name] == ['read_document', 'expand_document_context']
    text = json.loads(client.chat_with_meta.call_args.args[0][1]['content'].split(': ', 1)[1])['text']
    assert text.startswith('--- Page 3 ---') and 'XOR ra 1 khi' in text
    assert len(response.sources) == 1
    assert response.sources[0]['page'] == 3 and 'XOR' in response.sources[0]['excerpt']
