"""Saving an answer as a note writes a real file before the desk says so."""
from datetime import datetime

from PyQt6.QtGui import QGuiApplication

from rat.engine.answer_notes import save_answer_note
from rat.ui.quick_pdf_controller import QuickPDFController

SOURCE = [{"path": "/x/ly-thuyet.pdf", "page": 4, "excerpt": "Cổng XOR ra 1 khi hai đầu vào khác nhau."}]


def test_note_file_keeps_question_answer_and_cited_page(tmp_path):
    path = save_answer_note("Cổng XOR cho ra 1 khi nào?", "Khi hai đầu vào khác nhau.", SOURCE,
                            now=datetime(2026, 11, 16, 15, 20), folder=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.name == "2026-11-16 1520 - Cổng XOR cho ra 1 khi nào.md"
    assert text.startswith("# Cổng XOR cho ra 1 khi nào?\n\nKhi hai đầu vào khác nhau.")
    assert "Nguồn: ly-thuyet.pdf · trang 4" in text and "> Cổng XOR ra 1" in text
    again = save_answer_note("Cổng XOR cho ra 1 khi nào?", "x", (), now=datetime(2026, 11, 16, 15, 20), folder=tmp_path)
    assert again != path and again.name.endswith("(2).md")


def _controller(tmp_path, monkeypatch):
    monkeypatch.setenv("RAT_NOTES_DIR", str(tmp_path / "notes"))
    QGuiApplication.instance() or QGuiApplication([])
    ctrl = QuickPDFController(auto_init_finder=False)
    ctrl.ready()
    return ctrl


def test_save_request_writes_the_answer_on_screen(tmp_path, monkeypatch):
    ctrl = _controller(tmp_path, monkeypatch)
    try:
        pdf = tmp_path / "a.pdf"
        turn = ctrl.conversation.begin_turn("Cổng NAND là gì?", kind="chat")
        ctrl.conversation.complete_turn(turn.turn_ref.turn_id, "Cổng vạn năng.", execution_id=turn.execution_id,
                                        source_refs=[{"path": str(pdf), "page": 1, "excerpt": "NAND la cong van nang."}])
        ctrl._displayed_turn_id = turn.turn_ref.turn_id

        assert ctrl.submit("Lưu phần này thành ghi chú") is True
        files = list((tmp_path / "notes").glob("*.md"))
        assert len(files) == 1 and "Cổng vạn năng." in files[0].read_text(encoding="utf-8")
        assert files[0].stem in ctrl.snapshot["answerText"] and ctrl.snapshot["busy"] is False

        # Saving again saves the answer, not the "đã lưu" receipt that is now on screen.
        assert ctrl.submit("lưu ghi chú") is True
        texts = sorted(f.read_text(encoding="utf-8") for f in (tmp_path / "notes").glob("*.md"))
        assert len(texts) == 2 and all("Cổng vạn năng." in t for t in texts)
    finally:
        ctrl.close()


def test_save_with_nothing_to_save_says_so_and_writes_nothing(tmp_path, monkeypatch):
    ctrl = _controller(tmp_path, monkeypatch)
    try:
        assert ctrl.submit("Lưu phần này thành ghi chú") is True
        assert "Chưa có câu trả lời nào để lưu" in ctrl.snapshot["answerText"]
        assert not (tmp_path / "notes").exists()
    finally:
        ctrl.close()


def test_saving_a_quiz_turn_keeps_the_questions_not_the_receipt(tmp_path):
    quiz = {"title": "Trắc nghiệm · a.pdf (Trang 4)", "generator": "model", "questions": [
        {"question": "XOR ra 1 khi nào?", "options": ["A. Hai đầu vào giống", "B. Hai đầu vào khác"],
         "correct_index": 1, "quote": "XOR ra 1 khi hai đầu vào khác nhau."}]}
    path = save_answer_note("Tạo quiz", "Đã tạo 1 câu trắc nghiệm.", [{"path": "/x/a.pdf", "page": 4}],
                            folder=tmp_path, quiz=quiz)
    text = path.read_text(encoding="utf-8")
    assert "Đã tạo 1 câu" not in text
    assert "1. XOR ra 1 khi nào?" in text and "- B. Hai đầu vào khác ✓" in text
    assert "Nguồn: a.pdf · trang 4" in text
