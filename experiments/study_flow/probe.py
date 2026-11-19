"""Drive ask → quiz → note on real documents with the local model (see RESULTS.md).

    QT_QPA_PLATFORM=offscreen uv run python experiments/study_flow/probe.py [wiki dsa toeic]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["RAT_NOTES_DIR"] = str(HERE / "out" / "notes")

from PyQt6.QtGui import QGuiApplication  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

from rat.ui.quick_pdf_controller import QuickPDFController  # noqa: E402

GITHUB = Path.home() / "Documents/Github"
DOCS = {
    "wiki": (GITHUB / "Assignment4/wikipedia_kinh_te_viet_nam.pdf",
             "Đến năm 2017 có bao nhiêu nước công nhận Việt Nam là nền kinh tế thị trường?"),
    "dsa": (GITHUB / "tdtu-dsa-cheatsheet/cheatsheet.pdf",
            "Quick sort trường hợp xấu nhất có độ phức tạp bao nhiêu?"),
    "toeic": (GITHUB / "toeic-prep/ngay-01.pdf",
              "Tranh chỉ có đồ vật, không có người thì đáp án đúng thường dùng cấu trúc gì?"),
}


def wait_idle(ctrl, timeout: float) -> float:
    t0 = time.monotonic()
    QTest.qWait(50)
    while ctrl.snapshot["busy"]:
        if time.monotonic() - t0 > timeout:
            raise TimeoutError(f"still busy after {timeout}s")
        QTest.qWait(50)
    return round(time.monotonic() - t0, 1)


def step(ctrl, text: str, timeout: float) -> dict:
    t0 = time.monotonic()
    handled = ctrl.submit(text)
    wait_idle(ctrl, timeout)
    snap = ctrl.snapshot
    card = snap.get("artifactCard")
    return {
        "request": text, "handled": handled, "seconds": round(time.monotonic() - t0, 1),
        "answer": snap["answerText"],
        "sources": [{k: v for k, v in s.items() if not str(k).startswith("excerpt")}
                    for s in snap.get("answerSources") or []],
        "card": {k: card.get(k) for k in ("visual_type", "source_page", "generator", "model_error", "instruction", "questions")}
        if card else None,
    }


def main(names: list[str]) -> None:
    app = QGuiApplication.instance() or QGuiApplication([])
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    for name in names:
        path, question = DOCS[name]
        ctrl = QuickPDFController(auto_init_finder=False)
        ctrl.ready()
        try:
            ctrl.selectFile(str(path))
            wait_idle(ctrl, 60)
            run = {"doc": str(path), "steps": [step(ctrl, question, 240),
                                               step(ctrl, "Tạo 5 câu trắc nghiệm từ phần này", 400),
                                               step(ctrl, "Lưu thành ghi chú", 30)]}
        finally:
            ctrl.close()
        (out / f"{name}.json").write_text(json.dumps(run, ensure_ascii=False, indent=2, default=str))
        print(name, [s["seconds"] for s in run["steps"]], flush=True)
    del app


if __name__ == "__main__":
    main(sys.argv[1:] or list(DOCS))
