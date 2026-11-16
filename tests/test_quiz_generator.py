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
    compile_quiz_items,
    extract_fallback_quiz,
    generate_quiz_from_text,
    is_quote_grounded,
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


def test_fallback_and_model_quiz_generation():
    fallback_items = extract_fallback_quiz(COMPUTER_ORG_SAMPLE, count=4, source_page=4)
    assert len(fallback_items) == 4
    for q in fallback_items:
        assert len(q["options"]) == 4
        assert 0 <= q["correct_index"] < 4
        assert q["grounded"] is True
        assert q["source_page"] == 4

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
    q = res["questions"][0]
    assert q["options"][q["correct_index"]].endswith("Cổng NAND")


def test_generate_quiz_capability_and_view_spec(tmp_path):
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


def test_quick_pdf_controller_quiz_shortcut_and_qml_interaction(tmp_path):
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
        snap = ctrl.snapshot
        assert snap["view"] == "answer"
        assert snap["artifactCard"] is not None
        assert snap["artifactCard"]["visual_type"] == "quiz"
        assert len(snap["artifactCard"]["questions"]) == 3
        assert snap["artifactCard"]["source_page"] == 1

        QTest.qWait(60)
        card = find_item(root, "answerArtifactCard")
        assert card is not None and card.isVisible() is True

        quote_lbl = find_item(root, "quizQuoteLabel_0")
        assert quote_lbl is not None and quote_lbl.isVisible() is False

        quiz_reset = find_item(root, "resetQuizButton")
        assert quiz_reset is not None and quiz_reset.isVisible() is False

        click(view, root, "quizOption_0_0")
        QTest.qWait(40)

        assert quote_lbl.isVisible() is True
        assert "Trang 1" in quote_lbl.property("text")
        assert quiz_reset.isVisible() is True

        click(view, root, "resetQuizButton")
        QTest.qWait(30)
        assert quote_lbl.isVisible() is False
        assert warnings == []
    finally:
        timer.stop()
        ctrl.close()
        view.close()
        view.setSource(QUrl())
        view.deleteLater()
        ctrl.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
