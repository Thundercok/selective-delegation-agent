"""Run 7: would dropping questions with a quote-supported distractor remove the ambiguous ones?

    uv run python experiments/generative_views/run7_distractor_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from rat.engine.quiz_generator import key_supported_by_quote  # noqa: E402

FLOW = HERE.parent / "study_flow"


def labelled(with_question: bool = False):
    """(source, key, distractors, quote, label, note) for every labelled question; with_question
    puts (question, options in delivered order) in place of note."""
    for run, lab in (("out4", "quiz_labels_rat.json"), ("out5", "quiz_labels_rat5.json")):
        labels = json.loads((HERE / lab).read_text())
        for s in "123":
            qs = json.loads((HERE / run / f"quiz_{s}.json").read_text())["payload"]["questions"]
            for i, q in enumerate(qs, 1):
                opts = [c.split(". ", 1)[-1] for c in q["choices"]]
                k = "ABCD".index(q["answer"])
                label = labels[s][str(i)]
                tail = (q["prompt"], opts) if with_question else (label[1] if len(label) > 1 else "",)
                yield (f"{run}/{s}/Q{i}", opts[k], opts[:k] + opts[k + 1:], q["quote"], label[0], *tail)
    labels = json.loads((FLOW / "labels.json").read_text())["quiz"]
    for doc in ("wiki", "dsa", "toeic"):
        qs = json.loads((FLOW / "out" / f"{doc}.json").read_text())["steps"][1]["card"]["questions"]
        for i, q in enumerate(qs, 1):
            opts = [c.split(". ", 1)[-1] for c in q["options"]]
            k = q["correct_index"]
            label = labels[doc][str(i)]
            tail = (q["question"], opts) if with_question else (label[1],)
            yield (f"flow/{doc}/Q{i}", opts[k], opts[:k] + opts[k + 1:], q["quote"], label[0], *tail)


def main() -> None:
    kept = dropped = 0
    tally = {"right": [0, 0], "ambiguous": [0, 0]}  # [total, dropped]
    for name, key, distractors, quote, label, note in labelled():
        if not key_supported_by_quote(key, quote):
            continue  # the current pipeline already drops it
        hits = [d for d in distractors if key_supported_by_quote(d, quote)]
        tally[label][0] += 1
        if hits:
            tally[label][1] += 1
        if hits or label == "ambiguous":
            print(f"{name:14} {label:9} {'DROP' if hits else 'keep'}  key={key!r}")
            for d in hits:
                print(f"{'':25} supported distractor: {d!r}")
            if label == "ambiguous":
                print(f"{'':25} label note: {note}")
    for label, (total, n) in tally.items():
        print(f"{label}: {n}/{total} dropped")


if __name__ == "__main__":
    main()
