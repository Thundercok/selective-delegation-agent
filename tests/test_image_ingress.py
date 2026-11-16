"""Unit tests for RAT image drop & clipboard ingress (Roadmap step 2.4)."""
import os
from pathlib import Path
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent, QMimeData, QUrl
from PyQt6.QtGui import QFont, QGuiApplication, QImage
from PyQt6.QtQuick import QQuickItem, QQuickView
from PyQt6.QtTest import QTest

from rat.engine.assistant_runtime import AgentResponse, AssistantRuntime
from rat.kernel.input_context import ImageInput
from rat.ui.chat_session import ConversationHistory
from rat.ui.image_input import (
    encode_image,
    image_from_bytes,
    image_from_mime,
    image_from_url,
    parse_pasted_mime_content,
)
from rat.ui.image_preview import ImagePreviewProvider
from rat.ui.quick_pdf_controller import QuickPDFController
import rat.ui.quick_pdf_controller as qpc_mod

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication([])
    app.setFont(QFont("Helvetica Neue", 13))
    return app


def _wait_for(predicate, timeout=5.0):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, "Timed out waiting for predicate"
        QTest.qWait(10)
    QTest.qWait(20)


def test_encode_and_read_image(tmp_path, qapp):
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(0xFF0000)
    img_input = encode_image(img, origin="dropped_image")
    assert isinstance(img_input, ImageInput)
    assert img_input.origin == "dropped_image"
    assert len(img_input.content) > 0
    assert img_input.content_sha256

    # From bytes
    from_b = image_from_bytes(img_input.content, origin="clipboard_image")
    assert from_b.origin == "clipboard_image"
    assert from_b.content_sha256 == img_input.content_sha256

    # From URL / file
    file_path = tmp_path / "test_sample.png"
    assert img.save(str(file_path), "PNG")
    from_url, name = image_from_url(QUrl.fromLocalFile(str(file_path)))
    assert name == "test_sample.png"
    assert from_url.origin == "dropped_file"
    assert from_url.source_file_sha256


def test_image_from_mime(tmp_path, qapp):
    img = QImage(32, 32, QImage.Format.Format_RGB32)
    img.fill(0x00FF00)
    mime = QMimeData()
    mime.setImageData(img)

    inp, label = image_from_mime(mime, clipboard=True)
    assert inp.origin == "clipboard_image"
    assert label == "Ảnh vừa dán"

    parsed = parse_pasted_mime_content(mime)
    assert parsed["kind"] == "image"
    assert parsed["image"].origin == "clipboard_image"


def test_image_preview_provider(qapp):
    img = QImage(40, 40, QImage.Format.Format_RGB32)
    img.fill(0x0000FF)
    inp = encode_image(img)

    provider = ImagePreviewProvider()
    url = provider.set_input(inp)
    assert url.startswith("image://mini-input/img-")

    retrieved, size = provider.requestImage(inp.input_id, None)
    assert not retrieved.isNull()
    assert size.width() > 0


def test_main_desk_image_drop_attaches_ocr_context_and_quick_prompts(tmp_path, monkeypatch, qapp):
    img = QImage(40, 40, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFF)
    path = tmp_path / "diagram.png"
    assert img.save(str(path), "PNG")

    monkeypatch.setattr(qpc_mod, "extract_image_ocr", lambda image_input, p: "Hello world from slide 1")

    controller = QuickPDFController(db_path=str(tmp_path / "db.sqlite"), auto_init_finder=False)
    controller.ready()
    warnings = []
    view = QQuickView()
    view.engine().warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))
    try:
        controller.openPdfDocument(str(path))
        _wait_for(lambda: not controller.snapshot["busy"])
        snap = controller.snapshot
        assert snap["activeContext"]["type"] == "image"
        assert snap["activeContext"]["title"] == "diagram.png"
        assert "24 ký tự OCR" in snap["activeContext"]["subtitle"]
        assert len(snap["quickPrompts"]) == 3
        assert snap["quickPrompts"][0]["label"] == "Dịch sang tiếng Việt"
        assert snap["quickPrompts"][0]["autoSubmit"] is True

        # Also verify dropImage path
        controller.clearActiveContext()
        assert controller.snapshot["activeContext"] is None
        assert controller.dropImage([QUrl.fromLocalFile(str(path))]) is True
        _wait_for(lambda: not controller.snapshot["busy"])
        assert controller.snapshot["activeContext"]["type"] == "image"

        # Verify QML rendering with image context
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.setInitialProperties({
            "liveController": controller,
            "reduceMotion": True,
            "mascotSource": QUrl.fromLocalFile(str(PROJECT / "rat/assets/rat_mascot_cutout.png")),
        })
        view.setSource(QUrl.fromLocalFile(str(PROJECT / "rat/ui/quick/PDFDesk.qml")))
        assert view.status() == QQuickView.Status.Ready, [e.toString() for e in view.errors()]
        root = view.rootObject()
        view.resize(700, 640)
        view.show()
        QTest.qWait(40)

        doc_btn = root.findChild(QQuickItem, "documentMenu")
        prompts_row = root.findChild(QQuickItem, "ambientPromptsRow")
        chips_row = root.findChild(QQuickItem, "suggestionChipsRow")
        assert doc_btn is not None and doc_btn.property("text") == "diagram.png"
        assert prompts_row is not None and prompts_row.property("visible") is True
        assert chips_row is not None and chips_row.property("visible") is False

        # Clicking chip action displays extracted OCR text
        assert controller.showCurrentImageSource() is True
        assert controller.snapshot["view"] == "answer"
        assert controller.snapshot["answerText"] == "Hello world from slide 1"
        assert warnings == []
    finally:
        controller.close()
        view.setSource(QUrl())
        view.close()
        view.deleteLater()
        controller.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_main_desk_image_drop_with_draft_submits_immediately(tmp_path, monkeypatch, qapp):
    from rat.config import config
    from rat.engine.slm import slm_engine

    monkeypatch.setattr(config, "db_path", str(tmp_path / "db.sqlite"))
    monkeypatch.setattr(config, "document_model_path", "")
    monkeypatch.setattr(config, "document_model_preload", False)
    monkeypatch.setattr(slm_engine, "is_service_running", lambda: pytest.fail("GUI probed model service"))
    monkeypatch.setattr(slm_engine, "list_installed_models", lambda: [])
    monkeypatch.setattr(qpc_mod, "extract_image_ocr", lambda image_input, p: "Quarterly revenue grew 20%.")

    img = QImage(40, 40, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFF)
    path = tmp_path / "slide.png"
    assert img.save(str(path), "PNG")

    run_calls = []

    class RecordingBackend:
        def run(self, query, **context):
            run_calls.append({"query": query, "context": context})
            return AgentResponse("Doanh thu quý tăng 20%.", [], 0, 0, 10)

    runtime = AssistantRuntime()
    runtime.run = RecordingBackend().run
    controller = QuickPDFController(
        assistant_runtime=runtime,
        conversation=ConversationHistory(),
        db_path=str(tmp_path / "db.sqlite"),
        auto_init_finder=False,
    )
    controller.ready()
    try:
        assert controller.dropImage(
            [QUrl.fromLocalFile(str(path))],
            "Dịch đoạn này sang tiếng Việt",
        ) is True
        _wait_for(lambda: not controller.snapshot["busy"])
        assert controller.snapshot["view"] == "answer"
        assert "Doanh thu quý tăng 20%." in controller.snapshot["answerText"]
        assert len(run_calls) == 1
        ctx = run_calls[0]["context"]
        assert any(
            src.get("kind") == "image"
            and src.get("name") == "slide.png"
            and "Quarterly revenue grew 20%." in src.get("content", "")
            for src in ctx["previous_sources"]
        )
    finally:
        controller.close()
        controller.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_main_desk_image_drop_empty_ocr_and_invalid_image_errors(tmp_path, monkeypatch, qapp):
    img = QImage(30, 30, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFF)
    path = tmp_path / "blank.png"
    assert img.save(str(path), "PNG")

    controller = QuickPDFController(db_path=str(tmp_path / "db.sqlite"), auto_init_finder=False)
    controller.ready()
    try:
        monkeypatch.setattr(qpc_mod, "extract_image_ocr", lambda image_input, p: "")
        assert controller.selectImageFile(str(path)) is True  # accepted; OCR runs in the background
        _wait_for(lambda: not controller.snapshot["busy"])
        assert controller.snapshot["errorCode"] == "ocr_empty"
        assert controller.snapshot["view"] == "error"

        missing = tmp_path / "missing.png"
        assert controller.selectImageFile(str(missing)) is False
        assert controller.snapshot["errorCode"] == "image_invalid"
        assert controller.snapshot["view"] == "error"

        # A real file with an image suffix is only decoded in the worker, so the
        # refusal and its reason arrive after the busy phase.
        corrupt = tmp_path / "corrupt.png"
        corrupt.write_bytes(b"not an image at all")
        assert controller.selectImageFile(str(corrupt)) is True
        _wait_for(lambda: not controller.snapshot["busy"])
        assert controller.snapshot["errorCode"] == "image_invalid"
        assert controller.snapshot["view"] == "error"
        assert controller._custom_error_text

        assert controller.dropImage([QUrl.fromLocalFile(str(path)), QUrl.fromLocalFile(str(path))]) is False
        assert controller.snapshot["errorCode"] == "image_multiple"
        assert controller.snapshot["view"] == "error"
    finally:
        controller.close()
        controller.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def _white_png(tmp_path, name="shot.png"):
    img = QImage(40, 40, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFF)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


def test_image_ocr_runs_off_the_gui_thread(tmp_path, monkeypatch, qapp):
    """Vision OCR takes ~0.3-1 s; running it on the GUI thread froze the desk."""
    import threading

    gui_thread = threading.current_thread()
    seen = {}

    def fake_ocr(image_input, p):
        seen["thread"] = threading.current_thread()
        return "Text from a background thread"

    monkeypatch.setattr(qpc_mod, "extract_image_ocr", fake_ocr)
    controller = QuickPDFController(db_path=str(tmp_path / "db.sqlite"), auto_init_finder=False)
    controller.ready()
    try:
        assert controller.selectImageFile(str(_white_png(tmp_path))) is True
        assert controller.snapshot["busy"] is True
        assert controller.snapshot["title"] == "Đang đọc chữ trong ảnh."
        _wait_for(lambda: not controller.snapshot["busy"])
        assert seen["thread"] is not gui_thread
        assert controller.snapshot["activeContext"]["type"] == "image"
    finally:
        controller.close()
        controller.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_cancelling_image_ocr_drops_the_result_and_leaves_busy_view(tmp_path, monkeypatch, qapp):
    import threading

    release = threading.Event()

    def slow_ocr(image_input, p):
        release.wait(2)
        return "Late text"

    monkeypatch.setattr(qpc_mod, "extract_image_ocr", slow_ocr)
    controller = QuickPDFController(db_path=str(tmp_path / "db.sqlite"), auto_init_finder=False)
    controller.ready()
    try:
        assert controller.selectImageFile(str(_white_png(tmp_path)), "Dịch ảnh này") is True
        assert controller.snapshot["view"] == "busy"
        controller.cancel()
        release.set()
        QTest.qWait(150)
        snap = controller.snapshot
        assert snap["busy"] is False
        assert snap["view"] == "none"
        assert snap["activeContext"] is None
    finally:
        controller.close()
        controller.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
