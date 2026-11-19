"""Verify RAT's crawler extractors integrate cleanly with the external `verified-document-intake` package."""

from __future__ import annotations

import pytest
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def _make_pdf(path, texts=("First page contents", "Second page contents"), password=None):
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(600, 800)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 30 750 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_metadata({"/Title": "Synthetic document"})
    if password is not None:
        writer.encrypt(password)
    writer.write(path)


def test_rat_digital_fallback_keeps_page_markers(tmp_path, monkeypatch):
    from rat.crawler import extractors

    path = tmp_path / "test.pdf"
    _make_pdf(path)
    monkeypatch.setattr(extractors.platform, "system", lambda: "Linux")
    text = extractors.extract_text_from_pdf(str(path))
    assert "Title: Synthetic document" in text
    assert "--- Page 2 ---\nSecond page contents" in text
    assert extractors.extract_text_from_pdf(str(tmp_path / "missing.pdf")) == ""


@pytest.mark.parametrize("data", [b"", b"not a PDF", b"%PDF-1.7\ntruncated"])
def test_rat_returns_empty_on_corrupt_pdf(tmp_path, monkeypatch, data):
    from rat.crawler import extractors

    monkeypatch.setattr(extractors.platform, "system", lambda: "Linux")
    path = tmp_path / "bad.pdf"
    path.write_bytes(data)
    assert extractors.extract_text_from_pdf(str(path)) == ""


def test_rat_returns_empty_on_encrypted_or_blank_pdf(tmp_path, monkeypatch):
    from rat.crawler import extractors

    monkeypatch.setattr(extractors.platform, "system", lambda: "Linux")
    locked = tmp_path / "locked.pdf"
    _make_pdf(locked, password="secret")
    assert extractors.extract_text_from_pdf(str(locked)) == ""

    scanned = tmp_path / "scanned.pdf"
    Image.new("RGB", (100, 100), color="white").save(scanned, "PDF")
    assert extractors.extract_text_from_pdf(str(scanned)) == ""


def test_rat_pdf_output_limit_includes_metadata_and_markers(tmp_path, monkeypatch):
    from rat.crawler import extractors

    path = tmp_path / "digital.pdf"
    _make_pdf(path)
    monkeypatch.setattr(extractors.platform, "system", lambda: "Linux")
    monkeypatch.setattr(extractors, "MAX_CHARS_PER_DOC", 10)
    assert len(extractors.extract_text_from_pdf(str(path))) == 10
