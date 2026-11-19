"""Tests for causal-schema grounded quiz generation, capability dispatch, and QML study card."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent, QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQuick import QQuickItem, QQuickView
from PyQt6.QtTest import QTest

from rat.engine.quiz_generator import (
    QUIZ_GENERATION_SCHEMA,
    QUIZ_INSTRUCTION,
    compile_quiz_items,
    generate_quiz_from_text,
    is_quote_grounded,
    key_supported_by_quote,
    quiz_failure_message,
    strip_choice_prefix,
)
from rat.kernel.capabilities import build_default_registry
from rat.kernel.capabilities.views import view_quiz
from rat.kernel.contracts import ArtifactStore
from rat.kernel.dispatcher import ActionDispatcher
from rat.ui.quick_app import bind_desk_window
from rat.ui.quick_pdf_controller import QuickPDFController
from tests.test_quick_pdf import click, find_item, wait_for
from tests.test_selected_pdf import write_pdf


COMPUTER_ORG_SAMPLE = (
    "Cổng AND cho đầu ra bằng 1 khi tất cả các đầu vào đều bằng 1.\n"
    "Cổng OR cho đầu ra bằng 1 khi có ít nhất một đầu vào bằng 1.\n"
    "Cổng XOR cho đầu ra bằng 1 khi hai đầu vào có giá trị khác nhau.\n"
    "Mạch tổ hợp có đầu ra chỉ phụ thuộc vào tổ hợp giá trị đầu vào hiện tại.\n"
    "Mọi hàm logic Boolean đều có thể được xây dựng chỉ bằng cổng NAND vạn năng.\n"
)

PDF_ASCII_SAMPLE = (
    "The AND gate outputs 1 only when all input signals are equal to 1. "
    "The OR gate outputs 1 whenever at least one input signal is equal to 1. "
    "The XOR gate outputs 1 when its two input values are different from each other. "
    "Every Boolean logic function can be constructed using universal NAND gates alone."
)

ASCII_ITEMS = [
    {"a_quote": "The AND gate outputs 1 only when all input signals are equal to 1.",
     "b_question": "When does the AND gate output 1?", "c_correct": "When all input signals are equal to 1",
     "d_distractors": ["When the two inputs differ", "When no input is 1", "Never"]},
    {"a_quote": "The OR gate outputs 1 whenever at least one input signal is equal to 1.",
     "b_question": "When does the OR gate output 1?", "c_correct": "When at least one input signal is equal to 1",
     "d_distractors": ["Only when all inputs are 0", "When the two inputs differ", "Never"]},
    {"a_quote": "The XOR gate outputs 1 when its two input values are different from each other.",
     "b_question": "When does the XOR gate output 1?", "c_correct": "When its two input values are different",
     "d_distractors": ["When both inputs are 0", "When no input is 1", "Never"]},
    {"a_quote": "Every Boolean logic function can be constructed using universal NAND gates alone.",
     "b_question": "Which gate alone can build every Boolean function?", "c_correct": "Universal NAND gates",
     "d_distractors": ["Inverters", "Flip-flops", "Multiplexers"]},
]


@pytest.fixture
def quiz_model(monkeypatch):
    """The local model, faked: it writes the four ASCII_ITEMS questions."""
    model = MagicMock()
    model.chat_with_meta.return_value = {"message": {"content": json.dumps({"items": ASCII_ITEMS})}}
    monkeypatch.setattr("rat.engine.quiz_generator._default_quiz_client", lambda: model)
    return model


def test_causal_schema_order_and_compile_invariants():
    item_props = QUIZ_GENERATION_SCHEMA["properties"]["items"]["items"]["properties"]
    assert list(item_props.keys()) == ["a_quote", "b_question", "c_correct", "d_distractors"]
    assert strip_choice_prefix("B. Cổng XOR") == "Cổng XOR"

    raw = [
        {
            "a_quote": "Cổng XOR cho đầu ra bằng 1 khi hai đầu vào có giá trị khác nhau.",
            "b_question": "Cổng XOR cho đầu ra bằng 1 khi nào?",
            "c_correct": "A. Khi hai đầu vào khác nhau",
            "d_distractors": [
                "B. Khi cả hai đầu vào bằng 0",
                "Khi cả hai đầu vào bằng 1",
                "Khi không có đầu vào nào",
            ],
        },
        {
            # Duplicate distractor matching correct should drop cleanly so bad items don't poison the quiz
            "a_quote": "Ngắn",
            "b_question": "Bad question",
            "c_correct": "Same text",
            "d_distractors": ["Same text", "Only one unique", "Only one unique"],
        },
    ]
    compiled = compile_quiz_items(raw, source_text=COMPUTER_ORG_SAMPLE, source_page=4, max_count=5)
    assert len(compiled) == 1
    q = compiled[0]
    assert len(q["options"]) == 4
    assert q["options"][q["correct_index"]].endswith("Khi hai đầu vào khác nhau")
    assert q["source_page"] == 4
    assert q["grounded"] is True
    assert is_quote_grounded("Một câu hoàn toàn bịa đặt không có trong sách về tàu vũ trụ.", COMPUTER_ORG_SAMPLE) is False


def test_model_quiz_generation():
    mock_model = MagicMock()
    mock_model.chat_with_meta.return_value = {
        "message": {
            "content": json.dumps(
                {
                    "items": [
                        {
                            "a_quote": "Mọi hàm logic Boolean đều có thể được xây dựng chỉ bằng cổng NAND vạn năng.",
                            "b_question": "Cổng logic nào được gọi là cổng vạn năng có thể dựng mọi hàm Boolean?",
                            "c_correct": "Cổng NAND",
                            "d_distractors": ["Chỉ cổng AND", "Chỉ cổng OR", "Chỉ bộ đếm nhị phân"],
                        }
                    ]
                }
            )
        }
    }
    res = generate_quiz_from_text(
        COMPUTER_ORG_SAMPLE,
        title="Ôn tập Cổng logic",
        count=3,
        source_page=4,
        model_client=mock_model,
    )
    assert res["visual_type"] == "quiz"
    assert res["question_count"] == 1
    assert res["grounded_count"] == 1
    assert res["generator"] == "model" and res["model_error"] is None
    assert mock_model.chat_with_meta.call_args.kwargs["timeout"] >= 180
    q = res["questions"][0]
    assert q["options"][q["correct_index"]].endswith("Cổng NAND")


def test_generate_quiz_capability_and_view_spec(tmp_path, quiz_model):
    pdf_path = write_pdf(tmp_path / "ComputerOrg.pdf", [PDF_ASCII_SAMPLE])
    reg = build_default_registry()
    assert reg.has_operation("generate_quiz")
    store = ArtifactStore()
    dispatcher = ActionDispatcher(reg, store)

    res = dispatcher.execute_operation(
        "generate_quiz",
        {"file_path": str(pdf_path), "page": 1, "count": 3},
    )
    assert res.status == "success"
    assert res.artifact is not None
    assert res.artifact.kind == "quiz"
    assert res.artifact.payload["source_page"] == 1
    assert len(res.artifact.payload["questions"]) == 3

    spec = view_quiz(res.artifact, {})
    assert spec.schema_version == 1
    assert "ComputerOrg.pdf" in spec.title
    assert len(spec.blocks) == 2


def test_quick_pdf_controller_quiz_shortcut_and_qml_interaction(tmp_path, quiz_model, monkeypatch):
    monkeypatch.setenv("RAT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("RAT_NOTES_DIR", str(tmp_path / "notes"))
    _app = QGuiApplication.instance() or QGuiApplication([])
    pdf_path = write_pdf(tmp_path / "ToChucMayTinh.pdf", [PDF_ASCII_SAMPLE])
    ctrl = QuickPDFController(auto_init_finder=False)
    ctrl.ready()
    ctrl.setExpanded(True)

    view = QQuickView()
    warnings: list[str] = []
    view.engine().warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setInitialProperties({"liveController": ctrl, "reduceMotion": True})
    view.setSource(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "rat/ui/quick/PDFDesk.qml")))
    assert view.status() == QQuickView.Status.Ready, [e.toString() for e in view.errors()]
    root = view.rootObject()
    view.resize(620, 680)
    timer = bind_desk_window(view)
    view.show()

    try:
        ctrl.selectFile(str(pdf_path))
        wait_for(lambda: not ctrl.snapshot["busy"])
        ctrl.setExpanded(True)

        handled = ctrl.submit("tạo 3 câu trắc nghiệm trang 1")
        assert handled is True
        # Written off the UI thread: the desk shows busy, then the card arrives.
        assert ctrl.snapshot["busy"] is True
        wait_for(lambda: not ctrl.snapshot["busy"])
        snap = ctrl.snapshot
        assert snap["view"] == "answer"
        assert snap["artifactCard"] is not None
        assert snap["artifactCard"]["visual_type"] == "quiz"
        assert len(snap["artifactCard"]["questions"]) == 3
        assert snap["artifactCard"]["source_page"] == 1

        QTest.qWait(60)
        card = find_item(root, "answerArtifactCard")
        assert card is not None and card.isVisible() is True

        instruction = find_item(root, "quizInstruction")
        assert instruction is not None and instruction.isVisible() is True
        assert instruction.property("text") == QUIZ_INSTRUCTION

        quote_lbl = find_item(root, "quizQuoteLabel_0")
        assert quote_lbl is not None and quote_lbl.isVisible() is False

        quiz_reset = find_item(root, "resetQuizButton")
        assert quiz_reset is not None and quiz_reset.isVisible() is False

        click(view, root, "quizOption_0_0")
        QTest.qWait(40)

        assert quote_lbl.isVisible() is True
        assert "Trang 1" in quote_lbl.property("text")
        assert quiz_reset.isVisible() is True

        # The user marks question 1 wrong: it is logged, greyed, and the chosen answer stays.
        flag = find_item(root, "quizFlag_0")
        assert flag is not None and flag.isVisible() is True
        assert find_item(root, "quizFlag_1").isVisible() is False  # not answered yet
        click(view, root, "quizFlag_0")
        QTest.qWait(40)
        assert find_item(root, "quizFlagged_0").isVisible() is True and flag.isVisible() is False
        assert quote_lbl.isVisible() is True
        [line] = (tmp_path / "state" / "quiz_flags.jsonl").read_text(encoding="utf-8").splitlines()
        logged = json.loads(line)
        first = snap["artifactCard"]["questions"][0]
        assert logged["question"] == first["question"] and logged["page"] == 1
        assert logged["doc"] == str(pdf_path) and logged["generator"] == "model"

        click(view, root, "resetQuizButton")
        QTest.qWait(30)
        assert quote_lbl.isVisible() is False
        assert find_item(root, "quizFlagged_0").isVisible() is True  # "Làm lại" does not undo a flag
        assert warnings == []

        assert ctrl.submit("Lưu thành ghi chú") is True
        wait_for(lambda: not ctrl.snapshot["busy"])
        [note] = (tmp_path / "notes").glob("*.md")
        text = note.read_text(encoding="utf-8")
        assert first["question"] not in text and "Đã bỏ 1 câu bạn đánh dấu sai" in text
        assert text.count("\n1. ") == 1 and "\n2. " in text and "\n3. " not in text
    finally:
        timer.stop()
        ctrl.close()
        view.close()
        view.setSource(QUrl())
        view.deleteLater()
        ctrl.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_without_a_working_model_there_is_no_quiz_and_it_says_why(tmp_path):
    # Page-built questions were removed: 6/20 and 10/20 bad (experiments/study_flow/RESULTS.md).
    broken = MagicMock()
    broken.chat_with_meta.return_value = {"message": {}, "error": "timeout"}
    res = generate_quiz_from_text(COMPUTER_ORG_SAMPLE, count=2, source_page=4, model_client=broken)
    assert res["questions"] == [] and res["generator"] == "none" and res["model_error"] == "timeout"

    res = generate_quiz_from_text(COMPUTER_ORG_SAMPLE, count=2)  # no model under pytest
    assert res["questions"] == [] and res["model_error"] == "model_unavailable"
    assert "Ollama" in quiz_failure_message("model_unavailable")
    assert "Ollama" not in quiz_failure_message("no_grounded_items")

    pdf_path = write_pdf(tmp_path / "ToChucMayTinh.pdf", [PDF_ASCII_SAMPLE])
    dispatcher = ActionDispatcher(build_default_registry(), ArtifactStore())
    res = dispatcher.execute_operation("generate_quiz", {"file_path": str(pdf_path), "page": 1})
    assert "Ollama" in str(res.error or res.data)

    _app = QGuiApplication.instance() or QGuiApplication([])
    ctrl = QuickPDFController(auto_init_finder=False)
    ctrl.ready()
    try:
        ctrl.selectFile(str(pdf_path))
        wait_for(lambda: not ctrl.snapshot["busy"])
        assert ctrl.submit("tạo 3 câu trắc nghiệm trang 1") is True
        wait_for(lambda: not ctrl.snapshot["busy"])
        assert ctrl.snapshot["artifactCard"] is None
        assert "Ollama" in ctrl.snapshot["answerText"]
    finally:
        ctrl.close()


def test_quiz_on_this_part_uses_the_page_the_last_answer_cited(tmp_path, quiz_model):
    _app = QGuiApplication.instance() or QGuiApplication([])
    pdf_path = write_pdf(tmp_path / "ToChucMayTinh.pdf", [PDF_ASCII_SAMPLE, PDF_ASCII_SAMPLE])
    ctrl = QuickPDFController(auto_init_finder=False)
    ctrl.ready()
    try:
        ctrl.selectFile(str(pdf_path))
        wait_for(lambda: not ctrl.snapshot["busy"])
        turn = ctrl.conversation.begin_turn("Cổng NAND là gì?", kind="chat")
        ctrl.conversation.complete_turn(turn.turn_ref.turn_id, "Cổng vạn năng.", execution_id=turn.execution_id,
                                        source_refs=[{"path": str(pdf_path), "page": 2}])
        ctrl._displayed_turn_id = turn.turn_ref.turn_id

        assert ctrl.submit("Tạo 2 câu trắc nghiệm từ phần này") is True
        wait_for(lambda: not ctrl.snapshot["busy"])
        snap = ctrl.snapshot
        assert snap["artifactCard"]["source_page"] == 2
        assert "trang 2, trang câu trả lời vừa rồi dẫn" in snap["answerText"]
        assert snap["artifactCard"]["generator"] == "model"
    finally:
        ctrl.close()


def test_answer_positions_rotate_across_the_set():
    items = [{"a_quote": f"Đáp án đúng {i}", "b_question": f"Câu {i}?", "c_correct": f"Đáp án đúng {i}",
              "d_distractors": [f"sai {i}a", f"sai {i}b", f"sai {i}c"]} for i in range(4)]
    compiled = compile_quiz_items(items, source_text=" ".join(f"Đáp án đúng {i}." for i in range(4)), max_count=4)
    assert sorted(q["correct_index"] for q in compiled) == [0, 1, 2, 3]
    assert all(q["options"][q["correct_index"]].endswith(f"đúng {i}") for i, q in enumerate(compiled))


PAGE4_HEADER = "Cổng Biểu thức Ra 1 khi 00 01 10 11"
PAGE4_XOR = "XOR x ⊕ y = x'y + xy' hai đầu vào khác nhau 0 1 1 0"


def test_a_key_its_quote_does_not_state_is_dropped():
    # Runs 4-5: the table header was quoted for a question that names no gate, so several options were true.
    header_items = [
        {"a_quote": PAGE4_HEADER, "b_question": "Trong bảng chân trị, đầu ra bằng 1 khi nào?",
         "c_correct": "Đầu ra bằng 1 khi các đầu vào có giá trị cụ thể theo từng ô trong bảng",
         "d_distractors": ["Ít nhất một đầu vào bằng 1", "Tất cả đầu vào bằng 0", "Hai đầu vào khác nhau"]},
        {"a_quote": PAGE4_HEADER, "b_question": "Trong bảng chân trị, điều nào đúng về đầu ra khi đầu vào là 00, 01, 10, 11?",
         "c_correct": "Cổng AND có giá trị ra bằng 1 khi tất cả các đầu vào bằng 1",
         "d_distractors": ["Cổng OR ra 1 khi ít nhất một bằng 1", "Cổng NOR ra 1 khi tất cả bằng 0", "Cổng XOR ra 1 khi khác nhau"]},
    ]
    xor_item = {"a_quote": PAGE4_XOR, "b_question": "Cổng XOR ra 1 khi nào?", "c_correct": "Hai đầu vào khác nhau",
                "d_distractors": ["Cả hai đầu vào bằng 1", "Cả hai đầu vào bằng 0", "Tất cả đầu vào bằng 1"]}
    compiled = compile_quiz_items([*header_items, xor_item], source_text=PAGE4_HEADER + "\n" + PAGE4_XOR)
    assert [q["question"] for q in compiled] == ["Cổng XOR ra 1 khi nào?"]
    assert key_supported_by_quote("Hai đầu vào khác nhau", PAGE4_XOR)
    assert not key_supported_by_quote("Cổng AND có giá trị ra bằng 1 khi tất cả các đầu vào bằng 1", PAGE4_HEADER)


def test_a_value_key_passes_when_the_quote_holds_it():
    # Live run 2026-11-19: "NAND khi hai đầu vào bằng 1 thì ra bao nhiêu?" -> "0" was dropped as unsupported.
    nand_row = "NAND (xy)' không phải tất cả bằng 1 1 1 1 0"
    assert key_supported_by_quote("0", nand_row)
    assert not key_supported_by_quote("8", nand_row)
    assert not key_supported_by_quote("", nand_row)
    # Study flow run, DSA cheatsheet: a one-word key quoted from the Big-O table.
    assert key_supported_by_quote("n²", "Quick nlogn nlogn n² logn ✗")
    assert not key_supported_by_quote("n²", "Merge nlogn nlogn nlogn n ✓")


def test_quiz_says_how_its_questions_are_answered():
    model = MagicMock()
    model.chat_with_meta.return_value = {"message": {"content": json.dumps({"items": [{
        "a_quote": "Cổng XOR cho đầu ra bằng 1 khi hai đầu vào có giá trị khác nhau.",
        "b_question": "Cổng XOR ra 1 khi nào?", "c_correct": "Hai đầu vào có giá trị khác nhau",
        "d_distractors": ["Hai đầu vào bằng 0", "Hai đầu vào bằng 1", "Không bao giờ"]}]})}}
    quiz = generate_quiz_from_text(COMPUTER_ORG_SAMPLE, count=1, model_client=model)
    assert quiz["generator"] == "model" and quiz["instruction"] == QUIZ_INSTRUCTION
    assert "đầy đủ nhất" in QUIZ_INSTRUCTION
