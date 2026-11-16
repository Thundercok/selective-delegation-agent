"""Can a model compose a usable screen on demand from a fixed component catalog?

Three requests (tarot spread, electricity bills, quiz from a chapter), N samples
each, against a local Ollama model. Writes raw specs, checks and an HTML render
per sample to out/. Usage:

    uv run python experiments/generative_views/run.py [--model qwen3:4b-instruct] [--samples 3]

Limits of this proxy: the bills are synthetic structured data (no PDF
extraction), HTML stands in for QML, and only one model family is tested.
"""
from __future__ import annotations

import argparse
import html
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from views_catalog import BLOCKS, invented_numbers, resolve, validate  # noqa: E402

OUT = HERE / "out"
OLLAMA = "http://localhost:11434/api/chat"
COURSE_PDF = Path.home() / "Documents/Github/tdtu-computer-organization/ly-thuyet-giua-ky-502044.pdf"
QUIZ_PAGE = 4  # "3. Cổng logic"

MAJOR_ARCANA = [
    ("The Fool", "khởi đầu mới, liều lĩnh, tin vào bước nhảy"),
    ("The Magician", "đủ công cụ trong tay, biến ý định thành việc"),
    ("The High Priestess", "trực giác, điều chưa nói ra"),
    ("The Empress", "nuôi dưỡng, sung túc, sáng tạo"),
    ("The Emperor", "trật tự, kỷ luật, cấu trúc"),
    ("The Hierophant", "truyền thống, người dẫn dắt, khuôn phép"),
    ("The Lovers", "lựa chọn theo giá trị, gắn kết"),
    ("The Chariot", "ý chí, tiến lên bằng kiểm soát"),
    ("Strength", "can đảm mềm mỏng, kiên nhẫn"),
    ("The Hermit", "rút lui để nhìn rõ, tự soi xét"),
    ("Wheel of Fortune", "chu kỳ, bước ngoặt ngoài tầm tay"),
    ("Justice", "công bằng, nhân quả, quyết định rõ ràng"),
    ("The Hanged Man", "tạm dừng, nhìn từ góc khác"),
    ("Death", "kết thúc để chuyển hoá"),
    ("Temperance", "cân bằng, pha trộn đúng liều"),
    ("The Devil", "ràng buộc, thói quen khó bỏ"),
    ("The Tower", "đổ vỡ đột ngột, sự thật lộ ra"),
    ("The Star", "hy vọng, hồi phục"),
    ("The Moon", "mơ hồ, lo âu, điều chưa rõ"),
    ("The Sun", "rõ ràng, niềm vui, thành công"),
    ("Judgement", "thức tỉnh, đánh giá lại"),
    ("The World", "hoàn tất, trọn vẹn một chặng"),
]


def tarot_task(seed: int) -> dict:
    rng = random.Random(seed)  # the draw is code, not the model
    positions = ["Quá khứ", "Hiện tại", "Tương lai"]
    cards = [{"position": pos, "name": name, "meaning": meaning, "reversed": rng.random() < 0.3}
             for pos, (name, meaning) in zip(positions, rng.sample(MAJOR_ARCANA, 3))]
    return {"id": "tarot", "request": "Trải 3 lá tarot cho tôi: quá khứ, hiện tại, tương lai.",
            "payload": {"spread": "Quá khứ – Hiện tại – Tương lai", "cards": cards},
            "actions": ["draw_again", "save_reading"]}


def bills_task() -> dict:
    # Synthetic data, labelled as such; a real run would extract these from bill PDFs.
    bills = [
        {"month": "2026-06", "kwh": 182, "amount_vnd": 512400, "due_date": "2026-07-10"},
        {"month": "2026-07", "kwh": 236, "amount_vnd": 689300, "due_date": "2026-08-10"},
        {"month": "2026-08", "kwh": 251, "amount_vnd": 741800, "due_date": "2026-09-10"},
        {"month": "2026-09", "kwh": 204, "amount_vnd": 583100, "due_date": "2026-10-10"},
        {"month": "2026-10", "kwh": 167, "amount_vnd": 466900, "due_date": "2026-11-10"},
        {"month": "2026-11", "kwh": 158, "amount_vnd": 438200, "due_date": "2026-12-10"},
    ]
    return {"id": "bills", "request": "Làm bảng theo dõi tiền điện từ mấy hoá đơn này, có hạn đóng gần nhất.",
            "payload": {"source": "6 hoá đơn EVN (dữ liệu giả lập cho thí nghiệm)", "bills": bills,
                        "latest": bills[-1], "next_due": bills[-1]["due_date"]},
            "actions": ["add_bill", "set_reminder"]}


def chat(model: str, messages: list, schema: dict, seed: int) -> tuple[str, float]:
    body = json.dumps({"model": model, "messages": messages, "stream": False, "format": schema,
                       "options": {"temperature": 0.3, "seed": seed}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        content = json.loads(resp.read())["message"]["content"]
    return content, time.perf_counter() - t0


QUESTIONS_SCHEMA = {
    "type": "object", "required": ["questions"],
    "properties": {"questions": {"type": "array", "items": {
        "type": "object", "required": ["prompt", "choices", "answer", "source_page"],
        "properties": {"prompt": {"type": "string"},
                       "choices": {"type": "array", "items": {"type": "string"}},
                       "answer": {"type": "string", "enum": ["A", "B", "C", "D"]},
                       "source_page": {"type": "integer"}}}}},
}


def quiz_task(model: str, seed: int) -> tuple[dict, dict]:
    from pypdf import PdfReader
    text = PdfReader(str(COURSE_PDF)).pages[QUIZ_PAGE - 1].extract_text()
    messages = [
        {"role": "system", "content": "Bạn soạn câu hỏi trắc nghiệm CHỈ từ đoạn tài liệu được đưa. "
         "Mỗi câu có đúng 4 lựa chọn, một đáp án đúng (A-D), và source_page là số trang của đoạn đó."},
        {"role": "user", "content": f"Trang {QUIZ_PAGE}:\n{text}\n\nSoạn 10 câu trắc nghiệm tiếng Việt."},
    ]
    raw, secs = chat(model, messages, QUESTIONS_SCHEMA, seed)
    questions = json.loads(raw)["questions"]
    for q in questions:
        q["choices"] = [f"{'ABCD'[i]}. {c}" for i, c in enumerate(q["choices"])]
    checks = {
        "count": len(questions),
        "four_choices": sum(len(q["choices"]) == 4 for q in questions),
        "cites_page": sum(q["source_page"] == QUIZ_PAGE for q in questions),
        "seconds": round(secs, 1),
    }
    task = {"id": "quiz", "request": "Tạo 10 câu trắc nghiệm từ chương 3 (Cổng logic), chấm điểm khi tôi nộp.",
            "payload": {"chapter": "3. Cổng logic", "document": COURSE_PDF.name, "questions": questions},
            "actions": ["submit_quiz", "export_pdf"]}
    return task, checks


VIEW_SCHEMA = {
    "type": "object", "required": ["title", "blocks"],
    "properties": {"title": {"type": "string"}, "blocks": {"type": "array", "items": {
        "type": "object", "required": ["type", "data"],
        "properties": {"type": {"type": "string", "enum": sorted(BLOCKS)}, "data": {"type": "object"}}}}},
}


def shape(value, depth=0):
    """Payload outline with one sample item, so the model sees field names and types."""
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(value[0], depth + 1), f"... {len(value)} items"] if value else []
    return value


def compose(model: str, task: dict, seed: int) -> tuple[str, float]:
    catalog = "\n".join(f"- {name}: {b['doc']} Bắt buộc: {b['required']}. Tuỳ chọn: {b['optional']}."
                        for name, b in BLOCKS.items())
    system = (
        "Bạn dựng màn hình cho một ứng dụng desktop bằng cách ghép các khối có sẵn. Trả về JSON "
        '{"title": ..., "blocks": [{"type": ..., "data": {...}}]}, tối đa 8 khối.\n'
        f"Các khối:\n{catalog}\n"
        "Luật: dữ liệu chỉ được đưa vào bằng tham chiếu. *_field là đường dẫn có dấu chấm vào payload "
        "(ví dụ latest.kwh). *_key là tên trường bên trong từng phần tử của danh sách. "
        "Không chép giá trị hay số từ payload vào title, label, text. "
        f"Chỉ dùng các action trong danh sách cho phép."
    )
    user = (f"Yêu cầu của người dùng: {task['request']}\n"
            f"Cấu trúc payload: {json.dumps(shape(task['payload']), ensure_ascii=False)}\n"
            f"Action cho phép: {task['actions']}")
    return chat(model, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                VIEW_SCHEMA, seed)


# ---------------------------------------------------------------- HTML render

def render(spec: dict, payload: dict) -> str:
    e = html.escape
    parts = [f"<h1>{e(spec.get('title', ''))}</h1>"]
    for block in spec.get("blocks", []):
        t, d = block.get("type"), block.get("data", {})
        get = (lambda ref: resolve(payload, ref))
        try:
            if t == "summary":
                text = get(d["text_field"]) if "text_field" in d else d.get("text", "")
                parts.append(f"<section><h2>{e(d['title'])}</h2><p>{e(str(text))}</p></section>")
            elif t == "stat":
                parts.append(f"<section class=stat><b>{e(str(get(d['value_field'])))}</b> "
                             f"{e(d.get('unit', ''))}<div>{e(d['label'])}</div></section>")
            elif t == "card_grid":
                cards = "".join(
                    f"<div class='card {'down' if d.get('face') == 'down' else ''}' onclick=\"this.classList.toggle('down')\">"
                    f"<b>{e(str(it.get(d['title_key'], '')))}</b>"
                    + (f"<span class=badge>{e(d['badge_key'])}</span>" if d.get("badge_key") and it.get(d["badge_key"]) else "")
                    + f"<i>{e(str(it.get(d.get('subtitle_key', ''), '')))}</i>"
                    f"<p>{e(str(it.get(d.get('body_key', ''), '')))}</p></div>" for it in get(d["items_field"]))
                parts.append(f"<section class=grid style='--cols:{int(d.get('per_row', 3))}'>{cards}</section>")
            elif t == "metric_chart":
                items = get(d["items_field"])
                ys = [float(it[d["y_key"]]) for it in items]
                w, h, top = 60 * len(ys), 160, max(ys) or 1
                if d["kind"] == "line":
                    pts = " ".join(f"{30 + 60 * i},{h - 20 - (y / top) * (h - 40)}" for i, y in enumerate(ys))
                    marks = f"<polyline fill=none stroke=currentColor stroke-width=2 points='{pts}'/>"
                else:
                    marks = "".join(f"<rect x={10 + 60 * i} y={h - 20 - (y / top) * (h - 40)} width=40 "
                                    f"height={(y / top) * (h - 40)} fill=currentColor />" for i, y in enumerate(ys))
                labels = "".join(f"<text x={30 + 60 * i} y={h - 4} font-size=10 text-anchor=middle>"
                                 f"{e(str(it[d['x_key']]))}</text>" for i, it in enumerate(items))
                parts.append(f"<section><h2>{e(d.get('title', ''))} ({e(d.get('unit', ''))})</h2>"
                             f"<svg width={w} height={h}>{marks}{labels}</svg></section>")
            elif t == "table":
                cols = d["columns"]
                head = "".join(f"<th>{e(c.get('label', c['key']))}</th>" for c in cols)
                rows = "".join("<tr>" + "".join(f"<td>{e(str(it.get(c['key'], '')))}</td>" for c in cols) + "</tr>"
                               for it in get(d["items_field"]))
                parts.append(f"<section><h2>{e(d.get('title', ''))}</h2><table><tr>{head}</tr>{rows}</table></section>")
            elif t == "quiz":
                qs = "".join(
                    f"<li>{e(str(q[d['prompt_key']]))}<ul>" + "".join(f"<li>{e(c)}</li>" for c in q[d["choices_key"]])
                    + f"</ul><details><summary>Đáp án</summary>{e(str(q[d['answer_key']]))}"
                    + (f" · trang {e(str(q.get(d['source_key'], '')))}" if d.get("source_key") else "")
                    + "</details></li>" for q in get(d["items_field"]))
                parts.append(f"<section><h2>{e(d.get('title', ''))}</h2><ol>{qs}</ol></section>")
            elif t == "actions":
                parts.append("<section>" + "".join(f"<button>{e(a)}</button>" for a in d.get("action_ids", []))
                             + "</section>")
        except Exception as exc:  # render what we can, flag what we can't
            parts.append(f"<section class=err>Không dựng được khối {e(str(t))}: {e(repr(exc))}</section>")
    style = ("body{font:14px -apple-system,sans-serif;max-width:760px;margin:24px auto;padding:0 16px}"
             "section{border:1px solid #ddd;border-radius:8px;padding:12px;margin:10px 0}"
             ".grid{display:grid;grid-template-columns:repeat(var(--cols),1fr);gap:8px}"
             ".card{border:1px solid #999;border-radius:8px;padding:10px;cursor:pointer;min-height:90px}"
             ".card.down>*{visibility:hidden}.card.down{background:repeating-linear-gradient(45deg,#335,#335 6px,#446 6px,#446 12px)}"
             ".card i{display:block;color:#666}.badge{margin-left:6px;font-size:11px;background:#fde;padding:1px 6px;border-radius:6px}.stat b{font-size:32px}.err{color:#b00}"
             "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}")
    return f"<!doctype html><meta charset=utf-8><style>{style}</style>{''.join(parts)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:4b-instruct")
    ap.add_argument("--samples", type=int, default=3)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    results = []
    for seed in range(1, args.samples + 1):
        quiz, quiz_checks = quiz_task(args.model, seed)
        for task in (tarot_task(seed), bills_task(), quiz):
            raw, secs = compose(args.model, task, seed)
            row = {"task": task["id"], "seed": seed, "model": args.model, "seconds": round(secs, 1)}
            if task["id"] == "quiz":
                row["questions"] = quiz_checks
            try:
                spec = json.loads(raw)
            except json.JSONDecodeError as exc:
                row.update(parse_error=str(exc), errors=["not JSON"])
                results.append(row)
                continue
            row["errors"] = validate(spec, task["payload"], task["actions"])
            try:
                row["invented_numbers"] = invented_numbers(spec, task["payload"])
            except NotImplementedError:
                row["invented_numbers"] = "pending"
            row["block_types"] = [b.get("type") for b in spec.get("blocks", []) if isinstance(b, dict)]
            name = f"{task['id']}_{seed}"
            (OUT / f"{name}.json").write_text(json.dumps({"spec": spec, "payload": task["payload"]},
                                                         ensure_ascii=False, indent=2))
            (OUT / f"{name}.html").write_text(render(spec, task["payload"]))
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
