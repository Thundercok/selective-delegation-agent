"""Build the fill-in-the-blank fallback quiz on four real pages (see RESULTS.md).

    uv run python experiments/study_flow/cloze_probe.py          # round 1 pages
    uv run python experiments/study_flow/cloze_probe.py round2   # pages never tuned on
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from document_intake.pdf import read_pdf_native  # noqa: E402
from cloze import extract_fallback_quiz  # noqa: E402  (this folder is on sys.path)

GITHUB = Path.home() / "Documents/Github"
PAGES = {
    "gates": (GITHUB / "tdtu-computer-organization/ly-thuyet-giua-ky-502044.pdf", 4),
    "wiki": (GITHUB / "Assignment4/wikipedia_kinh_te_viet_nam.pdf", 3),
    "dsa": (GITHUB / "tdtu-dsa-cheatsheet/cheatsheet.pdf", 1),
    "toeic": (GITHUB / "toeic-prep/ngay-01.pdf", 2),
}
ROUND2 = {
    "orgnotes": (GITHUB / "tdtu-computer-organization/computer-organization-502044-midterm-notes.pdf", 3),
    "toeic8": (GITHUB / "toeic-prep/lo-trinh-toeic-8-tuan.pdf", 3),
    "proposal": (GITHUB / "tdtu-research-proposal-guides/Student_Research_Proposal_Guide_TDTU_2026.pdf", 3),
    "imlbook": (GITHUB / "tdtu-student-submissions/524k0001-524k0002-524k0003/Interpretable_Machine_Learning_Book.pdf", 3),
}


def page_text(path: Path, page: int) -> str:
    text = read_pdf_native(str(path))
    text = text if isinstance(text, str) else getattr(text, "text", str(text))
    parts = re.split(r"--- Page (\d+) ---", text)
    pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    return pages[page]


def main(round_name: str) -> None:
    out = {}
    for name, (path, page) in (ROUND2 if round_name == "round2" else PAGES).items():
        quiz = extract_fallback_quiz(page_text(path, page), count=5, source_page=page)
        out[name] = quiz
        qs = quiz
        print(f"\n=== {name} p{page}: {len(qs)} questions")
        for i, q in enumerate(qs, 1):
            print(f"Q{i}. {q['question']}")
            for j, c in enumerate(q["options"]):
                print("    ", c, "  <-- key" if j == q["correct_index"] else "")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / ("cloze_round2.json" if round_name == "round2" else "cloze.json")).write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "round1")
