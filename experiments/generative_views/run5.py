"""Run 5: RAT's quiz generator with the one-correct-answer prompt (rat/engine/quiz_generator.py) on the same page 4.

The model writes quote, question, correct answer as text and 3 distractors; code
shuffles and assigns letters. Same settings as RAT's SLM client (temperature 0.1,
num_ctx 8192) plus a seed per sample. Writes out5/quiz_N.json in the shape
verify.py reads (prompt, choices, answer letter). Usage:

    PYTHONPATH=. uv run python experiments/generative_views/run5.py [--seeds 3]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from rat.engine.quiz_generator import generate_quiz_from_text  # noqa: E402
from verify import QUIZ_PAGE, page_text  # noqa: E402

OUT = HERE / "out5"


class SeededOllama:
    def __init__(self, model: str, seed: int):
        self.model, self.seed = model, seed

    def chat_with_meta(self, messages, tools, response_format=None, max_tokens=4096, **_kw):
        body = {"model": self.model, "messages": messages, "stream": False, "format": response_format,
                "options": {"temperature": 0.1, "num_predict": max_tokens, "num_ctx": 8192, "seed": self.seed}}
        req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:4b-instruct")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    page = page_text()
    for seed in range(1, args.seeds + 1):
        t0 = time.perf_counter()
        quiz = generate_quiz_from_text(page, count=10, source_page=QUIZ_PAGE,
                                       model_client=SeededOllama(args.model, seed))
        secs = round(time.perf_counter() - t0, 1)
        questions = [{"prompt": q["question"], "choices": q["options"], "answer": "ABCD"[q["correct_index"]],
                      "quote": q["quote"], "grounded": q["grounded"]} for q in quiz["questions"]]
        (OUT / f"quiz_{seed}.json").write_text(json.dumps({"payload": {"questions": questions}, "seconds": secs},
                                                          ensure_ascii=False, indent=2))
        print(seed, secs, "questions", len(questions), "grounded", quiz["grounded_count"], flush=True)


if __name__ == "__main__":
    main()
