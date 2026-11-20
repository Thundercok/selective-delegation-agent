"""Test suite for RAT built-in instant tools: Web Reader and Timetable."""

from unittest.mock import patch

from rat.engine.web_reader import extract_url, fetch_web_summary


def test_extract_url():
    assert extract_url("xem https://vnexpress.net/thoi-su ngay") == "https://vnexpress.net/thoi-su"
    assert extract_url("khong co link") is None
    assert extract_url("http://example.org/test?a=1&b=2") == "http://example.org/test?a=1&b=2"


def test_fetch_web_summary_mocked():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tin Tức Công Nghệ 2026</title>
        <meta name="description" content="Khám phá các tiến bộ đột phá trong trí tuệ nhân tạo và mô hình ngôn ngữ nhỏ.">
    </head>
    <body>
        <h1>Tiêu đề chính</h1>
        <p>Các nhà nghiên cứu vừa công bố kỹ thuật can thiệp mô hình giúp suy luận từng bước rõ ràng hơn.</p>
        <p>Hệ thống hoạt động trực tiếp trên thiết bị cá nhân mà không phụ thuộc vào máy chủ đám mây.</p>
    </body>
    </html>
    """
    with patch(
        "socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
    ), patch(
        "rat.engine.web_reader._single_hop_httpx",
        return_value=(200, {"content-type": "text/html"}, sample_html),
    ):
        res = fetch_web_summary("https://tech-news.vn/article/123")
        assert res["visual_type"] == "web"
        assert res["title"] == "Tin Tức Công Nghệ 2026"
        assert res["domain"] == "tech-news.vn"
        assert len(res["bullets"]) >= 1
        assert "tiến bộ đột phá" in res["summary"]


def test_controller_instant_dispatch():
    from PyQt6.QtGui import QGuiApplication

    _app = QGuiApplication.instance() or QGuiApplication([])
    from rat.engine.assistant_runtime import AssistantRuntime
    from rat.ui.quick_pdf_controller import QuickPDFController

    runtime = AssistantRuntime()
    ctrl = QuickPDFController(assistant_runtime=runtime)
    ctrl.ready()
    fake_web = {
        "visual_type": "web",
        "title": "Tin Tức Công Nghệ 2026",
        "domain": "tech-news.vn",
        "url": "https://tech-news.vn/article/123",
        "bullets": ["Mô hình chạy trực tiếp trên thiết bị cá nhân."],
        "summary": "Mô hình chạy trực tiếp trên thiết bị cá nhân.",
    }
    try:
        with patch("rat.engine.web_reader.fetch_web_summary", return_value=fake_web):
            handled = ctrl.submit("tóm tắt https://tech-news.vn/article/123")
        assert handled is True
        snap = ctrl.snapshot
        assert snap["view"] == "answer"
        assert snap["artifactCard"]["visual_type"] == "web"
        assert "Tin Tức Công Nghệ 2026" in snap["answerText"]
    finally:
        ctrl.close()
