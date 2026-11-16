"""Run 2 of the generative-view experiment: are run 1's composition failures cheap to fix?

Arm A: fixed catalog (stat takes dates, card_grid has badge_key, stricter checks)
and a tighter prompt. Arm B: A plus the list of fields that must be visible, as a
"what must be shown" step would supply. Both get one repair turn with the
validator's errors. Quiz questions are reused from run 1 (out/quiz_N.json), so
only composition is measured. Usage:

    uv run python experiments/generative_views/run2.py [--samples 3]

Pass = no structural errors, nothing in MUST_SHOW missing, no noise block.
MUST_SHOW and EXTRA are the experimenter's judgement of what each request needs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run import BLOCKS, VIEW_SCHEMA, bills_task, chat, render, shape, tarot_task
from views_catalog import coverage, invented_numbers, noise_blocks, validate

HERE = Path(__file__).resolve().parent
OUT = HERE / "out2"

MUST_SHOW = {
    "tarot": ["cards[].position", "cards[].name", "cards[].meaning", "cards[].reversed"],
    "bills": ["bills[].month", "bills[].amount_vnd", "next_due|latest.due_date"],
    "quiz": ["questions[].prompt", "questions[].choices", "questions[].answer"],
}
EXTRA = {
    "tarot": ("spread",),
    "bills": ("latest.amount_vnd", "latest.kwh", "bills[].kwh", "bills[].due_date", "source"),
    "quiz": ("questions[].source_page", "chapter", "document"),
}


def quiz_from_run1(seed: int) -> dict:
    saved = json.loads((HERE / "out" / f"quiz_{seed}.json").read_text())
    return {"id": "quiz", "request": "Tạo 10 câu trắc nghiệm từ chương 3 (Cổng logic), chấm điểm khi tôi nộp.",
            "payload": saved["payload"], "actions": ["submit_quiz", "export_pdf"]}


def messages_for(task: dict, arm: str) -> list[dict]:
    catalog = "\n".join(f"- {name}: {b['doc']} Bắt buộc: {b['required']}. Tuỳ chọn: {b['optional']}."
                        for name, b in BLOCKS.items())
    system = (
        "Bạn dựng màn hình cho một ứng dụng desktop bằng cách ghép các khối có sẵn. Trả về JSON "
        '{"title": ..., "blocks": [{"type": ..., "data": {...}}]}, tối đa 8 khối.\n'
        f"Các khối:\n{catalog}\n"
        "Luật:\n"
        "1. Dữ liệu chỉ được đưa vào bằng tham chiếu. *_field là đường dẫn có dấu chấm vào payload "
        "(ví dụ latest.kwh). *_key là tên trường bên trong từng phần tử của danh sách. "
        "Không chép giá trị hay số từ payload vào title, label, text.\n"
        "2. Chỉ dùng khối mà yêu cầu thật sự cần. Không thêm quiz, biểu đồ hay lưới thẻ nếu người dùng không hỏi tới.\n"
        "3. Mọi thông tin người dùng cần để làm việc họ hỏi phải hiện trên màn hình. "
        "Trường boolean như reversed dùng badge_key.\n"
        "4. Chỉ dùng các action trong danh sách cho phép."
    )
    user = (f"Yêu cầu của người dùng: {task['request']}\n"
            f"Cấu trúc payload: {json.dumps(shape(task['payload']), ensure_ascii=False)}\n"
            f"Action cho phép: {task['actions']}")
    if arm == "B":
        user += ("\nCác trường bắt buộc phải hiện (a|b nghĩa là một trong hai): "
                 + ", ".join(MUST_SHOW[task["id"]]))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def score(spec, task) -> dict:
    tid = task["id"]
    errors = validate(spec, task["payload"], task["actions"])
    if errors:
        return {"errors": errors, "missing": None, "noise": None, "passed": False}
    missing = coverage(spec, MUST_SHOW[tid])
    noise = noise_blocks(spec, MUST_SHOW[tid], EXTRA[tid])
    return {"errors": [], "missing": missing, "noise": noise, "passed": not missing and not noise}


def run_one(model: str, task: dict, arm: str, seed: int) -> dict:
    messages = messages_for(task, arm)
    row = {"task": task["id"], "arm": arm, "seed": seed}
    raw, secs = chat(model, messages, VIEW_SCHEMA, seed)
    row["seconds"] = round(secs, 1)
    spec = json.loads(raw)
    first = score(spec, task)
    row["first_try"] = first
    if first["errors"]:  # one repair turn, as a runtime with a validator would do
        messages += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": "Spec có lỗi, sửa và trả lại toàn bộ spec:\n- "
                      + "\n- ".join(first["errors"])}]
        raw, secs2 = chat(model, messages, VIEW_SCHEMA, seed)
        row["seconds"] = round(secs + secs2, 1)
        spec = json.loads(raw)
    final = score(spec, task)
    row.update(final=final, invented_numbers=invented_numbers(spec, task["payload"]),
               block_types=[b.get("type") for b in spec.get("blocks", []) if isinstance(b, dict)])
    name = f"{task['id']}_{arm}_{seed}"
    (OUT / f"{name}.json").write_text(json.dumps({"spec": spec, "payload": task["payload"]}, ensure_ascii=False, indent=2))
    try:
        (OUT / f"{name}.html").write_text(render(spec, task["payload"]))
    except Exception as exc:  # a broken spec should not stop the run
        row["render_error"] = repr(exc)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:4b-instruct")
    ap.add_argument("--samples", type=int, default=3)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    rows = []
    for seed in range(1, args.samples + 1):
        for task in (tarot_task(seed), bills_task(), quiz_from_run1(seed)):
            for arm in ("A", "B"):
                try:
                    row = run_one(args.model, task, arm, seed)
                except (json.JSONDecodeError, KeyError) as exc:
                    row = {"task": task["id"], "arm": arm, "seed": seed, "crash": repr(exc)}
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    (OUT / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    for arm in ("A", "B"):
        mine = [r for r in rows if r["arm"] == arm]
        print(arm, "first-try pass", sum(r.get("first_try", {}).get("passed", False) for r in mine),
              "final pass", sum(r.get("final", {}).get("passed", False) for r in mine), "of", len(mine))


if __name__ == "__main__":
    main()
