"""Blind human labels for intervention rows, to check the automatic outcome classifier.

Rules this module enforces:
- It opens a run only after that run's pre-registered ``analyze.py`` has run, so the
  labels cannot feed an analysis that is still open.
- Rows from every ``eval_*/*_interventions.jsonl`` of the run are pooled and shown in
  a shuffled order. The model/condition (the folder name), the row id, the flags and
  the automatic ``outcome`` are never shown.
- Labels go to ``<RAT_DIR>/labels/<run>.jsonl``, never into the research repo. The
  label file holds no automatic outcome; agreement reads it from the source at report
  time.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

LABELS = ("follows", "follows_rounded", "follows_approximate", "reverted", "moved", "other", "no_answer")
SHOWN_FIELDS = ("prefix", "old", "new", "expected", "original", "continuation")
WARNING = ("Chỉ dùng bàn gán nhãn sau khi analyze.py của run này đã chạy. "
           "Nhãn người không được đưa vào phân tích đã đăng ký trước.")


class LabelDeskError(ValueError):
    pass


def analysis_done(run_dir: Path) -> Tuple[bool, str]:
    """True only when the run's analyze.py finished (run.log ``done`` or a fresh analyze.log)."""
    script = run_dir / "analyze.py"
    if not script.is_file():
        return False, "Run này không có analyze.py, nên không biết phân tích đã đăng ký đã chạy hay chưa."
    log = run_dir / "run.log"
    if log.is_file():
        from rat.research.runs import is_terminal, parse_steps
        names = [name for name, _ in parse_steps(log.read_text(errors="replace"))]
        if names and is_terminal(names[-1]) and any("analysis" in name for name in names):
            return True, "run.log ghi bước phân tích rồi kết thúc."
    result = run_dir / "analyze.log"
    if result.is_file() and result.stat().st_size and result.stat().st_mtime >= script.stat().st_mtime:
        return True, "analyze.log mới hơn analyze.py."
    return False, "Chưa thấy analyze.py chạy xong (run.log chưa có done, analyze.log chưa có)."


@dataclass(frozen=True)
class Row:
    key: str
    source: str
    id: str
    fields: Dict


def blind_key(run: str, source: str, row_id: str) -> str:
    return hashlib.sha256(f"{run}\0{source}\0{row_id}".encode()).hexdigest()[:12]


class LabelDesk:
    def __init__(self, repo: Path, run: str, store_dir: Path):
        self.repo, self.run = Path(repo), run
        self.run_dir = self.repo / "audit" / run
        if not self.run_dir.is_dir():
            raise LabelDeskError(f"Không có run audit/{run} trong repo nghiên cứu.")
        ok, reason = analysis_done(self.run_dir)
        if not ok:
            raise LabelDeskError(f"Bàn gán nhãn bị khóa: {reason} {WARNING}")
        self.store = Path(store_dir).expanduser() / f"{run}.jsonl"
        if self.store.resolve().is_relative_to(self.repo.resolve()):
            raise LabelDeskError("Nhãn phải lưu ngoài repo nghiên cứu.")
        self.rows = self._load_rows()
        if not self.rows:
            raise LabelDeskError(f"audit/{run} không có tệp eval_*/*_interventions.jsonl.")
        order = sorted(self.rows)
        random.Random(f"rat-blind:{run}").shuffle(order)
        self.order = order

    def _load_rows(self) -> Dict[str, Row]:
        rows = {}
        for path in sorted(self.run_dir.glob("eval_*/*_interventions.jsonl")):
            source = str(path.relative_to(self.run_dir))
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                key = blind_key(self.run, source, str(data["id"]))
                rows[key] = Row(key, source, str(data["id"]), {f: data.get(f) for f in SHOWN_FIELDS})
        return rows

    def labels(self) -> Dict[str, str]:
        """Latest label per row; relabelling appends and the newest line wins."""
        result = {}
        if self.store.is_file():
            for line in self.store.read_text().splitlines():
                if line.strip():
                    entry = json.loads(line)
                    result[entry["key"]] = entry["label"]
        return result

    def next_row(self) -> Optional[Dict]:
        done = self.labels()
        for position, key in enumerate(self.order, 1):
            if key not in done:
                return {"key": key, "position": position, "total": len(self.order), **self.rows[key].fields}
        return None

    def record(self, key: str, label: str) -> None:
        if label not in LABELS:
            raise LabelDeskError(f"Nhãn phải là một trong: {', '.join(LABELS)}.")
        row = self.rows.get(key)
        if row is None:
            raise LabelDeskError("Không có hàng này trong run.")
        self.store.parent.mkdir(parents=True, exist_ok=True)
        entry = {"key": key, "source": row.source, "id": row.id, "label": label,
                 "labelled_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        with self.store.open("a") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def automatic_outcomes(self) -> Dict[str, str]:
        outcomes = {}
        for path in sorted(self.run_dir.glob("eval_*/*_interventions.jsonl")):
            source = str(path.relative_to(self.run_dir))
            for line in path.read_text().splitlines():
                if line.strip():
                    data = json.loads(line)
                    outcomes[blind_key(self.run, source, str(data["id"]))] = data.get("outcome")
        return outcomes

    def agreement(self) -> Dict:
        human = self.labels()
        auto = self.automatic_outcomes()
        pairs = [(human[k], auto[k]) for k in human if k in auto]
        return {"n": len(pairs), "total": len(self.order), "kappa": cohen_kappa(pairs),
                "observed_agreement": (sum(h == a for h, a in pairs) / len(pairs)) if pairs else None,
                "confusion": confusion_matrix(pairs)}


def confusion_matrix(pairs: Sequence[Tuple[str, str]], labels: Sequence[str] = LABELS) -> List[List[int]]:
    """Rows are human labels, columns automatic outcomes, both in ``labels`` order."""
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for human, auto in pairs:
        if human in index and auto in index:
            matrix[index[human]][index[auto]] += 1
    return matrix


def cohen_kappa(pairs: Sequence[Tuple[str, str]]) -> Optional[float]:
    """Cohen's kappa; None with no pairs or when chance agreement is already 1."""
    n = len(pairs)
    if not n:
        return None
    observed = sum(h == a for h, a in pairs) / n
    categories = {c for pair in pairs for c in pair}
    expected = sum((sum(h == c for h, _ in pairs) / n) * (sum(a == c for _, a in pairs) / n)
                   for c in categories)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)
