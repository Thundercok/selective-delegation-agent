"""Run 8: does qwen3:4b with thinking find the true distractors? (see RESULTS.md)

    uv run python experiments/generative_views/run8_model_checker.py [limit]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from run7_distractor_check import labelled  # noqa: E402
from rat.engine.quiz_generator import key_supported_by_quote  # noqa: E402

MODEL = "qwen3:4b"
SCHEMA = {"type": "object", "properties": {"true_options": {"type": "array", "items": {"type": "string", "enum": list("ABCD")}}},
          "required": ["true_options"]}
SYSTEM = ("Bạn là giám khảo kiểm tra câu hỏi trắc nghiệm. Với câu hỏi và bốn phương án, hãy xét TỪNG phương án: "
          "nó có phải là một câu trả lời đúng cho câu hỏi không, theo đoạn trích và theo kiến thức chuyên môn chính xác? "
          "Một phương án đúng một phần hoặc đúng trong một trường hợp riêng vẫn tính là đúng. "
          "Trả về danh sách chữ cái của MỌI phương án đúng.")


def check(quote: str, question: str, options: list[str]) -> tuple[list[str], float]:
    user = (f"Đoạn trích: {quote}\n\nCâu hỏi: {question}\n\n"
            + "\n".join(f"{'ABCD'[i]}. {o}" for i, o in enumerate(options)))
    body = {"model": MODEL, "stream": False, "think": True, "format": SCHEMA, "options": {"temperature": 0},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    t0 = time.monotonic()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        msg = json.loads(resp.read())["message"]
    return json.loads(msg["content"]).get("true_options", []), round(time.monotonic() - t0, 1)


def main(limit: int | None) -> None:
    out_path = HERE / "run8_out.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else {}
    n = 0
    for name, key, distractors, quote, label, question, options in labelled(with_question=True):
        if not key_supported_by_quote(key, quote):
            continue
        if limit is not None and n >= limit:
            break
        n += 1
        if name not in done:
            marked, secs = check(quote, question, options)
            key_letter = "ABCD"[options.index(key)]
            done[name] = {"label": label, "key": key_letter, "marked": marked, "seconds": secs}
            out_path.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        r = done[name]
        print(f"{name:14} {r['label']:9} key={r['key']} marked={r['marked']} {r['seconds']}s", flush=True)
    tally = {"right": [0, 0], "ambiguous": [0, 0]}
    for r in done.values():
        tally[r["label"]][0] += 1
        tally[r["label"]][1] += any(m != r["key"] for m in r["marked"])
    print({k: f"{d}/{t} dropped" for k, (t, d) in tally.items()},
          "key unmarked:", sum(r["key"] not in r["marked"] for r in done.values()),
          "mean s:", round(sum(r["seconds"] for r in done.values()) / max(1, len(done)), 1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
