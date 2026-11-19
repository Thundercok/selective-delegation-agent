"""Tests for multi-step routing, automatic tool-pack loading, and live step progress."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent, QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQuick import QQuickItem, QQuickView
from PyQt6.QtTest import QTest

from rat.engine.agent_types import AgentResponse, AgentStep
from rat.engine.assistant_runtime import AssistantRuntime
from rat.kernel.contracts import Artifact
from rat.ui.answer_presentation import format_process_steps
from rat.ui.quick_app import bind_desk_window
from rat.ui.quick_pdf_controller import QuickPDFController, is_multistep_query


_APP = None


@pytest.fixture(scope="module")
def app():
    global _APP
    _APP = QGuiApplication.instance() or QGuiApplication([])
    return _APP


def test_is_multistep_query_single_vs_compound():
    for single in (
        "",
        "thời khóa biểu thứ hai",
        "gieo quẻ kinh dịch hôm nay",
        "rút 3 lá bài lenormand",
        "xem https://example.com/demo",
    ):
        assert is_multistep_query(single) is False, f"Expected single-step: {single!r}"

    for multi in (
        "xem lịch học hôm nay rồi tìm tài liệu môn đó",
        "đọc https://example.com/demo rồi dịch sang tiếng Việt và lưu ghi chú",
        "rút 3 lá bài rồi kết hợp với bản đồ sao",
        "xem lịch học hôm nay và tạo câu hỏi ôn tập trắc nghiệm",
    ):
        assert is_multistep_query(multi) is True, f"Expected multi-step: {multi!r}"


def test_format_process_steps_general_and_legacy_modes():
    legacy_step = AgentStep(
        1,
        "Đọc trang",
        tool_name="read_document",
        tool_args={"file_path": "/tmp/notes.pdf"},
        duration_ms=12.0,
    )
    legacy = format_process_steps([legacy_step], "PASS", [{"path": "/tmp/notes.pdf", "page": 2}])
    assert [s["fullTitle"] for s in legacy] == ["1. Tìm đoạn", "2. Đối chiếu", "3. Trích nguồn"]

    multi_steps = [
        AgentStep(1, "Đọc trang web", tool_name="read_web_page", tool_args={"url": "https://example.com/a"}, duration_ms=42.0),
        AgentStep(2, "Dịch văn bản", tool_name="translate_text", tool_args={"text": "Hello world"}, error="offline_timeout", duration_ms=15.0),
        AgentStep(3, "Lưu ghi chú", tool_name="synthesize_smart_note", tool_args={"title": "Bản tóm tắt"}, duration_ms=18.0),
    ]
    formatted = format_process_steps(multi_steps, "UNKNOWN", [])
    assert [s["shortTitle"] for s in formatted] == ["Web", "Dịch", "Ghi chú", "Đối chiếu"]
    assert formatted[0]["detail"] == "Đọc trang web: https://example.com/a (42ms)"
    assert formatted[1]["status"] == "verified_fail"
    assert formatted[2]["status"] == "done"
    assert formatted[2]["fullTitle"] == "3. Lưu ghi chú"


class _FakeSignalWorker(QObject):
    finished = pyqtSignal()
    response_ready = pyqtSignal(object)
    step_completed = pyqtSignal(object)
    progress_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.started = False
        self.startup_error = None

    def start(self) -> None:
        self.started = True

    def requestInterruption(self) -> None:
        pass

    def isRunning(self) -> bool:
        return False


def test_submit_multistep_bypasses_instant_loads_packs_and_streams_steps(app):
    runtime = AssistantRuntime(active_tool_packs=[], discover_tools=True, use_live_model=False)
    ctrl = QuickPDFController(assistant_runtime=runtime, auto_init_finder=False)
    ctrl.ready()
    fake_worker = _FakeSignalWorker()

    try:
        assert not runtime.is_tool_pack_loaded("timetable")
        with patch("rat.ui.quick_pdf_controller.create_execution_worker", return_value=fake_worker) as mock_factory:
            ok = ctrl.submit("xem lịch học hôm nay rồi tóm tắt https://example.com")

        assert ok is True
        assert fake_worker.started is True
        assert mock_factory.call_count == 1
        assert runtime.is_tool_pack_loaded("timetable")
        assert ctrl.snapshot["busy"] is True
        assert ctrl.snapshot["artifactCard"] is None

        eid = ctrl._current_execution_id
        gen = ctrl._chat_generation

        step1 = AgentStep(1, "Đang xem lịch học", tool_name="get_schedule", tool_args={"target_date": "today"}, duration_ms=10.0)
        step2 = AgentStep(2, "Đang đọc trang web", tool_name="read_web_page", tool_args={"url": "https://example.com"}, duration_ms=25.0)
        ctrl._on_execution_step(eid, gen, step1)
        assert ctrl.snapshot["busy"] is True
        assert [s["shortTitle"] for s in ctrl.snapshot["processSteps"]] == ["Lịch", "Đối chiếu"]
        assert "Bước 1:" in ctrl.snapshot["status"]

        ctrl._on_execution_step(eid, gen, step2)
        assert [s["shortTitle"] for s in ctrl.snapshot["processSteps"]] == ["Lịch", "Web", "Đối chiếu"]
        assert "Bước 2:" in ctrl.snapshot["status"]

        step3 = AgentStep(3, "Đang lưu ghi chú", tool_name="synthesize_smart_note", tool_args={"title": "Tổng hợp"}, duration_ms=15.0)
        ctrl._on_execution_response(
            AgentResponse(
                answer="Đã xem lịch, đọc web và lưu ghi chú.",
                steps=[step1, step2, step3],
                total_time_ms=50.0,
                tool_call_count=3,
                token_estimate=100,
                execution_id=eid,
                answer_verification_status="PASS",
            )
        )
        snap = ctrl.snapshot
        assert snap["busy"] is False
        assert snap["view"] == "answer"
        assert [s["shortTitle"] for s in snap["processSteps"]] == ["Lịch", "Web", "Ghi chú", "Đối chiếu"]
        assert ctrl._live_steps == []
    finally:
        ctrl.close()


def test_qml_live_process_steps_row_renders_without_warnings(app):
    runtime = AssistantRuntime(active_tool_packs=[], discover_tools=True, use_live_model=False)
    ctrl = QuickPDFController(assistant_runtime=runtime, auto_init_finder=False)
    ctrl.ready()
    ctrl.setExpanded(True)
    fake_worker = _FakeSignalWorker()

    view = QQuickView()
    warnings: list[str] = []
    view.engine().warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setInitialProperties({"liveController": ctrl, "reduceMotion": True})
    view.setSource(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "rat/ui/quick/PDFDesk.qml")))
    assert view.status() == QQuickView.Status.Ready, [e.toString() for e in view.errors()]
    root = view.rootObject()
    view.resize(620, 560)
    timer = bind_desk_window(view)
    view.show()

    try:
        with patch("rat.ui.quick_pdf_controller.create_execution_worker", return_value=fake_worker):
            assert ctrl.submit("đọc https://example.com rồi dịch sang tiếng Việt")

        ctrl._on_execution_step(
            ctrl._current_execution_id,
            ctrl._chat_generation,
            AgentStep(1, "Đang đọc trang web", tool_name="read_web_page", tool_args={"url": "https://example.com"}, duration_ms=12.0),
        )
        ctrl._on_execution_step(
            ctrl._current_execution_id,
            ctrl._chat_generation,
            AgentStep(2, "Đang dịch văn bản", tool_name="translate_text", tool_args={"text": "Hi"}, duration_ms=8.0),
        )
        QTest.qWait(50)

        live_row = root.findChild(QQuickItem, "liveProcessStepsRow")
        assert live_row is not None
        assert live_row.isVisible() is True
        assert warnings == []
    finally:
        ctrl._on_execution_response(
            AgentResponse("Xong.", [], 20.0, 2, 10, execution_id=ctrl._current_execution_id)
        )
        timer.stop()
        ctrl.close()
        view.close()
        view.setSource(QUrl())
        view.deleteLater()
        ctrl.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_multistep_artifact_card_mounted_in_answer_view_without_warnings(app):
    ctrl = QuickPDFController(auto_init_finder=False)
    ctrl.ready()
    ctrl.setExpanded(True)
    assert ctrl.assistant_runtime.discover_tools is False

    view = QQuickView()
    warnings: list[str] = []
    view.engine().warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setInitialProperties({"liveController": ctrl, "reduceMotion": True})
    view.setSource(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "rat/ui/quick/PDFDesk.qml")))
    assert view.status() == QQuickView.Status.Ready, [e.toString() for e in view.errors()]
    root = view.rootObject()
    view.resize(620, 560)
    timer = bind_desk_window(view)
    view.show()

    try:
        artifacts = [
            Artifact(
                id="tbl-1",
                kind="result_table",
                revision=1,
                title="Hóa đơn & Hạn đóng",
                inputs={},
                payload={
                    "title": "Hóa đơn & Hạn đóng",
                    "headers": ["Khoản mục", "Số tiền"],
                    "rows": [["Tiền điện T11", "420.000đ"], ["Hạn thanh toán", "20/11/2026"]],
                    "summary": "Tổng hợp tự động.",
                },
            ),
            Artifact(
                id="sch-1",
                kind="schedule",
                revision=1,
                title="Lịch hôm nay",
                inputs={"target_date": "Hôm nay"},
                payload={"items": [{"time": "07:30 - 09:30", "course_name": "Toán rời rạc", "room": "A301", "instructor": "TS. An"}]},
            ),
            Artifact(
                id="web-1",
                kind="web_page_snapshot",
                revision=1,
                title="Trang tham khảo",
                inputs={},
                payload={
                    "final_url": "https://example.org/guide",
                    "title": "Hướng dẫn ôn tập",
                    "content": "Đây là đoạn nội dung hướng dẫn chi tiết cho bài kiểm tra giữa kỳ.\nDòng hai đủ dài để hiển thị trong thẻ tóm tắt.",
                },
            ),
        ]
        for expected_type, art in zip(("table", "timetable", "web"), artifacts):
            turn = ctrl.conversation.begin_turn(f"Test {expected_type}")
            ctrl._current_turn_id = turn.turn_id
            ctrl._current_execution_id = turn.execution_id
            ctrl._current_worker = _FakeSignalWorker()
            ctrl._on_execution_response(
                AgentResponse(
                    f"Kết quả {expected_type}",
                    [],
                    10.0,
                    1,
                    20,
                    artifacts=[art],
                    execution_id=turn.execution_id,
                )
            )
            QTest.qWait(40)
            snap = ctrl.snapshot
            assert snap["artifactCard"] is not None
            assert snap["artifactCard"]["visual_type"] == expected_type
            card_item = root.findChild(QQuickItem, "answerArtifactCard")
            assert card_item is not None and card_item.isVisible() is True

        # Also exercise fixed quiz template rendering cleanly
        ctrl._artifact_card = {
            "visual_type": "quiz",
            "title": "Ôn tập Cổng Logic",
            "questions": [
                {"question": "Cổng NAND cho đầu ra 0 khi nào?", "options": ["Tất cả ngõ vào là 1", "Có ít nhất một ngõ vào 0"], "correct_index": 0},
            ],
        }
        ctrl.changed.emit()
        QTest.qWait(40)
        card_item = root.findChild(QQuickItem, "answerArtifactCard")
        assert card_item is not None and card_item.isVisible() is True
        assert warnings == []
    finally:
        timer.stop()
        ctrl.close()
        view.close()
        view.setSource(QUrl())
        view.deleteLater()
        ctrl.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
