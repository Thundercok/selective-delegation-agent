"""CLI-to-UI on the real desk: "/rat ..." in the composer renders the command's ViewSpec."""
from __future__ import annotations

from PyQt6.QtQuick import QQuickItem

from tests.test_quick_unified_flow import app, quick_env, submit_draft, wait_for  # noqa: F401
from tests.test_research_desks import research_repo


def test_composer_command_renders_and_buttons_rerun_view_commands(quick_env, tmp_path, monkeypatch):
    monkeypatch.setenv("RAT_RESEARCH_REPO", str(research_repo(tmp_path)))
    monkeypatch.setattr("rat.config.RAT_DIR", tmp_path / "state")
    controller, root = quick_env.controller, quick_env.root
    submit_draft(quick_env.view, root, "/rat label demo_run")
    wait_for(lambda: controller.snapshot["view"] == "cli" and not controller.snapshot["cliBusy"])
    spec = controller.snapshot["cliView"]
    assert spec["title"] == "Gán nhãn · demo_run"
    view = root.findChild(QQuickItem, "cliView")
    assert view is not None and view.isVisible()

    follows = spec["blocks"][-1]["data"]["commands"][0]
    assert controller.runCliArgs(follows["argv"])
    wait_for(lambda: not controller.snapshot["cliBusy"])
    assert controller.snapshot["cliView"]["blocks"][1]["data"]["title"] == "Hàng 2/2"

    controller.closeCliView()
    assert controller.snapshot["view"] != "cli"


def test_paper_view_accepts_dropped_pdfs(quick_env, tmp_path, monkeypatch):
    from PyQt6.QtCore import QUrl
    monkeypatch.setattr("rat.config.RAT_DIR", tmp_path / "state")
    monkeypatch.setattr("rat.crawler.indexer.Indexer.index_single_file", lambda self, path: True)
    controller, root = quick_env.controller, quick_env.root
    assert controller.runCliView("/rat papers")
    wait_for(lambda: controller.snapshot["view"] == "cli" and not controller.snapshot["cliBusy"])
    zone = root.findChild(QQuickItem, "cliDropZone")
    assert zone is not None and zone.isVisible()

    pdf = tmp_path / "2401.00001.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    assert controller.runCliDrop(["papers", "add"], [QUrl.fromLocalFile(str(pdf)).toString()])
    wait_for(lambda: not controller.snapshot["cliBusy"])
    rows = controller.snapshot["cliView"]["blocks"][1]["data"]["rows"]
    assert rows == [["2401.00001.pdf", "đã lập chỉ mục"]]
    assert (tmp_path / "state" / "papers" / "2401.00001.pdf").is_file()
