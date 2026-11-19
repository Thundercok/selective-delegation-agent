"""Machine-generated run output stays out of the index; the documents beside it do not."""
from pathlib import Path

import pytest

from rat.crawler.indexer import Indexer


@pytest.fixture
def indexer():
    return Indexer.__new__(Indexer)  # is_ignored/discover_files need no database


@pytest.mark.parametrize("path", [
    "/u/Github/vrptw/results/run/shard_1/session/incumbent_000016.json",
    "/u/Github/proj/Outputs/eval.log",
    "/u/Github/proj/wandb/run-1/files/config.yaml",
])
def test_generated_output_is_ignored(indexer, path):
    assert indexer.is_ignored(Path(path))


@pytest.mark.parametrize("path", [
    "/u/Github/tdtu-computer-organization/ly-thuyet-giua-ky-502044.pdf",
    "/u/Documents/result_summary.docx",  # a file name, not a results/ folder
])
def test_documents_are_kept(indexer, path):
    assert not indexer.is_ignored(Path(path))


def test_discovery_does_not_descend_into_results(indexer, tmp_path):
    (tmp_path / "results" / "run").mkdir(parents=True)
    (tmp_path / "results" / "run" / "incumbent.json").write_text("{}")
    (tmp_path / "notes.md").write_text("# notes")
    indexer._cancel_flag = False
    assert indexer.discover_files([str(tmp_path)]) == [str(tmp_path / "notes.md")]


@pytest.mark.parametrize("path", [
    "/u/Downloads/vrptw-cd89d-firebase-adminsdk-fbsvc-af76407d0f.json",
    "/u/Downloads/Firebase-AdminSDK-Prod.JSON",
    "/u/Downloads/my-gcp-service-account-key.json",
    "/u/Downloads/client_secret_12345.json",
    "/u/Downloads/release.keystore",
])
def test_sensitive_credential_files_are_ignored(indexer, path):
    assert indexer.is_ignored(Path(path))


def test_binary_xml_with_nul_bytes_is_rejected_while_text_xml_is_allowed(tmp_path):
    from rat.crawler.indexer import is_binary_text_file

    binary_xml = tmp_path / "U0.xml"
    binary_xml.write_bytes(b"\x03\x00\x08\x00\x00\x00selector\x00\x01")
    text_xml = tmp_path / "layout.xml"
    text_xml.write_text("<manifest><app/></manifest>", encoding="utf-8")

    assert is_binary_text_file(binary_xml) is True
    assert is_binary_text_file(text_xml) is False


def test_purge_ignored_from_db_removes_secrets_and_binary_blobs(tmp_path):
    import numpy as np
    from rat.crawler.db import Database

    db = Database(str(tmp_path / "index.db"))
    try:
        empty_emb = np.empty((0, 384), dtype=np.float32)
        for p, text in [
            (str(tmp_path / "vrptw-firebase-adminsdk-123.json"), '{"private_key": "secret"}'),
            (str(tmp_path / "U0.xml"), "\x03\x00\x08\x00binary"),
            (str(tmp_path / "vrptw_report.md"), "Clean VRPTW report"),
        ]:
            db.replace_document({
                "file_path": p,
                "file_name": Path(p).name,
                "file_ext": Path(p).suffix,
                "file_size": 100,
                "created_at": 1.0,
                "modified_at": 1.0,
                "md5_hash": "abc",
                "content_text": text,
                "summary": "",
                "indexed_at": 1.0,
            }, [], empty_emb)

        idx = Indexer(db=db)
        purged = idx.purge_ignored_from_db()
        assert purged == 2
        assert db.get_document_by_path(str(tmp_path / "vrptw-firebase-adminsdk-123.json")) is None
        assert db.get_document_by_path(str(tmp_path / "U0.xml")) is None
        assert db.get_document_by_path(str(tmp_path / "vrptw_report.md")) is not None
    finally:
        db.get_connection().close()


def test_cli_index_purge_calls_purge_without_full_crawl(monkeypatch):
    from rat import cli

    calls = {"purge": 0, "discover": 0}

    class _FakeIndexer:
        def purge_ignored_from_db(self):
            calls["purge"] += 1
            return 3

        def discover_files(self, dirs):
            calls["discover"] += 1
            return []

    monkeypatch.setattr("rat.crawler.indexer.Indexer", _FakeIndexer)
    cli.cmd_index(None, purge=True)
    assert calls == {"purge": 1, "discover": 0}
