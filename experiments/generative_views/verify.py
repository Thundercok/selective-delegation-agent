"""Run 3: does a blind second pass catch wrong quiz answers? (2026-11-16)

For each run 1 question (out/quiz_N.json), a checker sees page 4 and the question
with its options, never the key. V1 solves it; V2 marks each option true or false.
Flags are scored against quiz_labels.json. Usage:

    uv run python experiments/generative_views/verify.py [--seeds 3]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run import COURSE_PDF, QUIZ_PAGE, chat

HERE = Path(__file__).resolve().parent
LETTERS = ["A", "B", "C", "D"]

V1_SCHEMA = {"type": "object", "required": ["answer", "other_correct"], "properties": {
    "answer": {"type": "string", "enum": LETTERS + ["NONE"]},
    "other_correct": {"type": "array", "items": {"type": "string", "enum": LETTERS}}}}
V2_SCHEMA = {"type": "object", "required": LETTERS,
             "properties": {k: {"type": "boolean"} for k in LETTERS}}


def page_text() -> str:
    from pypdf import PdfReader
    return PdfReader(str(COURSE_PDF)).pages[QUIZ_PAGE - 1].extract_text()


def duplicate_options(q: dict) -> bool:
    bodies = [c.split(". ", 1)[-1].strip().lower() for c in q["choices"]]
    return len(set(bodies)) < len(bodies)


def check_v1(model, page, q, seed):
    system = ("Bạn là người chấm đề. Chỉ dựa vào đoạn tài liệu. Chọn đáp án đúng của câu hỏi "
              "(answer). Nếu không có lựa chọn nào đúng thì answer = NONE. Liệt kê thêm mọi lựa "
              "chọn khác cũng đúng trong other_correct (để trống nếu không có).")
    user = f"Tài liệu (trang {QUIZ_PAGE}):\n{page}\n\nCâu hỏi: {q['prompt']}\n" + "\n".join(q["choices"])
    raw, _ = chat(model, [{"role": "system", "content": system}, {"role": "user", "content": user}], V1_SCHEMA, seed)
    out = json.loads(raw)
    others = sorted(set(out["other_correct"]) - {out["answer"]})
    flagged = out["answer"] != q["answer"] or out["answer"] == "NONE" or bool(others)
    return flagged, out


def check_v2(model, page, q, seed):
    system = ("Bạn là người chấm đề. Chỉ dựa vào đoạn tài liệu. Với từng lựa chọn A-D, trả true nếu "
              "lựa chọn đó là câu trả lời đúng cho câu hỏi theo tài liệu, false nếu không.")
    user = f"Tài liệu (trang {QUIZ_PAGE}):\n{page}\n\nCâu hỏi: {q['prompt']}\n" + "\n".join(q["choices"])
    raw, _ = chat(model, [{"role": "system", "content": system}, {"role": "user", "content": user}], V2_SCHEMA, seed)
    out = json.loads(raw)
    true_opts = [k for k in LETTERS if out[k]]
    flagged = true_opts != [q["answer"]]
    return flagged, out


def summarize(rows, checker, seeds):
    """Single run (seed 1) and union over seeds (flag if any seed flags)."""
    res = {}
    for name, pick in (("seed1", lambda r: r["flags"][checker][0]),
                       ("any_seed", lambda r: any(r["flags"][checker][:seeds]))):
        passed = [r for r in rows if not pick(r)]
        res[name] = {"bad_passed": sum(r["label"] != "right" for r in passed),
                     "right_passed": sum(r["label"] == "right" for r in passed),
                     "bad_total": sum(r["label"] != "right" for r in rows),
                     "right_total": sum(r["label"] == "right" for r in rows)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:4b-instruct")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--src", default="out")
    ap.add_argument("--labels", default="quiz_labels.json")
    ap.add_argument("--out", default="out3")
    args = ap.parse_args()
    out_dir = HERE / args.out
    out_dir.mkdir(exist_ok=True)
    page = page_text()
    labels = json.loads((HERE / args.labels).read_text())
    rows = []
    for qs in ("1", "2", "3"):
        questions = json.loads((HERE / args.src / f"quiz_{qs}.json").read_text())["payload"]["questions"]
        for i, q in enumerate(questions, 1):
            dup = duplicate_options(q)
            row = {"quiz": qs, "q": i, "label": labels[qs][str(i)][0], "key": q["answer"], "duplicate": dup,
                   "flags": {"v1": [], "v2": []}, "raw": {"v1": [], "v2": []}}
            for seed in range(1, args.seeds + 1):
                for name, fn in (("v1", check_v1), ("v2", check_v2)):
                    flagged, out = fn(args.model, page, q, seed)
                    row["flags"][name].append(flagged or dup)
                    row["raw"][name].append(out)
            rows.append(row)
            print(json.dumps({k: row[k] for k in ("quiz", "q", "label", "key", "duplicate", "flags")}), flush=True)
    summary = {c: summarize(rows, c, args.seeds) for c in ("v1", "v2")}
    (out_dir / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
