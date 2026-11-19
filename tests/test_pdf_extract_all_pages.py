"""The page that answers a question can be past page 25 (experiments/page_search/RESULTS.md)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QGuiApplication, QPainter, QPdfWriter

from rat.crawler.extractors import extract_document_content
from rat.engine.page_match import best_page, query_terms, split_pages


APP = None


def write_pdf(path, bodies):
    global APP
    # Keep the app referenced: an unreferenced one is collected and drawText aborts.
    APP = QGuiApplication.instance() or QGuiApplication([])
    writer = QPdfWriter(str(path))
    painter = QPainter(writer)
    for index, body in enumerate(bodies):
        if index:
            writer.newPage()
        painter.drawText(QPointF(200, 400), body)
    painter.end()


def test_a_slide_deck_is_read_past_page_25_and_its_late_page_can_be_picked(tmp_path):
    bodies = [f"Slide {n} pipeline stages overview" for n in range(1, 41)]
    bodies[37] = "Slide 38 branch prediction assumes not taken"
    pdf = tmp_path / "deck.pdf"
    write_pdf(pdf, bodies)

    content = extract_document_content(str(pdf))

    assert [n for n, _, _ in split_pages(content)] == list(range(1, 41))
    assert best_page(content, query_terms("branch prediction"))[0] == 38
