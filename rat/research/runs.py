"""Monitor research runs from ``audit/*/run.log`` and pause the running MLX job.

A run script writes one line per step: ``>>> <step> at <date>``. The last step is
``done`` when the script finished. The time left for the current step is estimated
from earlier steps of the same kind (``clean cf`` predicts ``clean plain``); with no
such step there is no estimate.

The machine runs one MLX job at a time, so RAT must not load its own MLX model while
a research job exists, even a paused one (SIGSTOP frees the GPU, not the memory).
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

STEP_LINE = re.compile(r"^>>> (?P<name>.+?) at (?P<date>.+)$")
JOB_PATTERN = re.compile(r"mlx_lm|structured_llm")
TREE_ROOT_PATTERN = re.compile(r"caffeinate|run\.sh")


def parse_date(text: str) -> Optional[datetime]:
    """Parse `date` output such as ``Sun Nov 15 17:20:56 +07 2026``."""
    parts = text.split()
    if len(parts) == 6:
        zone = parts[4]
        if re.fullmatch(r"[+-]\d{2}", zone):
            parts[4] = zone + "00"
        try:
            return datetime.strptime(" ".join(parts), "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            # A named zone (ICT): read it as local time.
            try:
                return datetime.strptime(" ".join(parts[:4] + parts[5:]), "%a %b %d %H:%M:%S %Y").astimezone()
            except ValueError:
                return None
    return None


def parse_steps(text: str) -> List[Tuple[str, datetime]]:
    steps = []
    for line in text.splitlines():
        match = STEP_LINE.match(line.strip())
        if match:
            when = parse_date(match["date"])
            if when is not None:
                steps.append((match["name"].strip(), when))
    return steps


@dataclass
class RunStatus:
    name: str
    log_path: str
    steps: List[Dict] = field(default_factory=list)
    current: Optional[str] = None
    elapsed_s: float = 0.0
    eta_s: Optional[float] = None
    done: bool = False


def is_terminal(step: str) -> bool:
    """Run scripts end with ``done``, ``finished`` or ``finished with status N``."""
    return step == "done" or step.startswith("finished")


def _kind(step: str) -> str:
    return step.split()[0] if step.split() else step


def run_status(log_path: Path, now: Optional[datetime] = None) -> RunStatus:
    steps = parse_steps(log_path.read_text(errors="replace"))
    status = RunStatus(name=log_path.parent.name, log_path=str(log_path))
    for index, (name, started) in enumerate(steps):
        ended = steps[index + 1][1] if index + 1 < len(steps) else None
        status.steps.append({"name": name, "started": started.isoformat(timespec="seconds"),
                             "duration_s": (ended - started).total_seconds() if ended else None})
    if not steps:
        return status
    name, started = steps[-1]
    if is_terminal(name):
        status.done = True
        return status
    now = now or datetime.now(started.tzinfo)
    status.current = name
    status.elapsed_s = max(0.0, (now - started).total_seconds())
    earlier = [s["duration_s"] for s in status.steps[:-1]
               if _kind(s["name"]) == _kind(name) and s["duration_s"]]
    if earlier:
        status.eta_s = max(0.0, sum(earlier) / len(earlier) - status.elapsed_s)
    return status


def list_runs(repo: Path) -> List[Path]:
    logs = (repo / "audit").glob("*/run.log")
    return sorted(logs, key=lambda p: p.stat().st_mtime, reverse=True)


def active_run(repo: Path, now: Optional[datetime] = None) -> Optional[RunStatus]:
    """The most recently written run whose last step is not terminal."""
    for log in list_runs(repo):
        status = run_status(log, now)
        if status.steps and not status.done:
            return status
    return None


# ---- processes -------------------------------------------------------------------

@dataclass(frozen=True)
class Proc:
    pid: int
    ppid: int
    stat: str
    command: str


def process_table() -> List[Proc]:
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,stat=,command="],
                         capture_output=True, text=True, check=False).stdout
    table = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
            table.append(Proc(int(parts[0]), int(parts[1]), parts[2], parts[3]))
    return table


def research_jobs(table: Sequence[Proc], own_pid: Optional[int] = None) -> List[Proc]:
    """Processes matching ``pgrep -f "mlx_lm|structured_llm"``, never RAT itself."""
    own = {own_pid or os.getpid(), os.getppid()}
    return [p for p in table if p.pid not in own and JOB_PATTERN.search(p.command)
            and "pgrep" not in p.command]


def job_tree(table: Sequence[Proc], own_pid: Optional[int] = None) -> List[Proc]:
    """The job plus its ``caffeinate``/``run.sh`` ancestors and all their descendants."""
    by_pid = {p.pid: p for p in table}
    roots = set()
    for job in research_jobs(table, own_pid):
        root, cursor = job.pid, by_pid.get(job.ppid)
        while cursor is not None and cursor.pid > 1:
            if TREE_ROOT_PATTERN.search(cursor.command):
                root = cursor.pid
            cursor = by_pid.get(cursor.ppid)
        roots.add(root)
    tree, frontier = set(roots), list(roots)
    while frontier:
        parent = frontier.pop()
        for p in table:
            if p.ppid == parent and p.pid not in tree:
                tree.add(p.pid)
                frontier.append(p.pid)
    return [by_pid[pid] for pid in sorted(tree)]


def is_paused(tree: Sequence[Proc]) -> bool:
    jobs = [p for p in tree if JOB_PATTERN.search(p.command)]
    return bool(jobs) and all("T" in p.stat for p in jobs)


def signal_tree(sig: int, table: Optional[Sequence[Proc]] = None, *, kill=os.kill) -> List[int]:
    tree = job_tree(table if table is not None else process_table())
    sent = []
    for proc in tree:
        try:
            kill(proc.pid, sig)
            sent.append(proc.pid)
        except ProcessLookupError:
            pass
    return sent


def pause(table=None, *, kill=os.kill) -> List[int]:
    return signal_tree(signal.SIGSTOP, table, kill=kill)


def resume(table=None, *, kill=os.kill) -> List[int]:
    return signal_tree(signal.SIGCONT, table, kill=kill)


class ResearchJobRunning(RuntimeError):
    pass


def ensure_no_research_mlx(table: Optional[Sequence[Proc]] = None) -> None:
    """Raise when a research MLX job exists: 16 GB fits one MLX job at a time."""
    if os.environ.get("RAT_ALLOW_MLX_WITH_RESEARCH") == "1":
        return
    jobs = research_jobs(table if table is not None else process_table())
    if jobs:
        raise ResearchJobRunning(
            f"research_mlx_job_running: pid {jobs[0].pid}. Máy 16 GB chỉ chạy một job MLX; "
            "đợi run nghiên cứu xong rồi mới nạp model của RAT.")


def monitor_line(status: Optional[RunStatus], tree: Sequence[Proc]) -> str:
    """One line for the tray: run, step, elapsed, estimate, paused."""
    def minutes(seconds):
        return f"{int(seconds // 60)} ph"
    if status is None:
        return "🧪 Không có run nghiên cứu" + (" · có job MLX" if tree else "")
    line = f"🧪 {status.name} · {status.current} · {minutes(status.elapsed_s)}"
    if status.eta_s is not None:
        line += f" · còn ~{minutes(status.eta_s)}"
    if is_paused(tree):
        line += " · ⏸"
    return line
