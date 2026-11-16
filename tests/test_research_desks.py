"""Run monitor, MLX guard, paper desk, blind labelling desk and the CLI-to-UI views."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from rat.research import labels, papers, runs
from rat.research.runs import Proc

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=7))


def stamp(hour, minute=0, day=15):
    return datetime(2026, 11, day, hour, minute, tzinfo=TZ).strftime("%a %b %d %H:%M:%S +07 %Y")


def write_log(run_dir: Path, steps):
    run_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, hour in steps:
        lines += [f">>> {name} at {stamp(hour)}", "noise from the step"]
    (run_dir / "run.log").write_text("\n".join(lines) + "\n")


ROWS = [
    {"id": "a1", "prefix": "<think>\nStep 1: 2*3=7\n", "old": 6.0, "new": 7.0, "expected": 8.0,
     "original": 7.0, "flags": [], "continuation": "Answer: 8", "outcome": "follows", "tokens": 9},
    {"id": "a2", "prefix": "<think>\nStep 1: 5+5=11\n", "old": 10.0, "new": 11.0, "expected": 12.0,
     "original": 11.0, "flags": ["x"], "continuation": "Answer: 11", "outcome": "reverted", "tokens": 9},
]


def research_repo(tmp_path, *, analysed=True) -> Path:
    repo = tmp_path / "research"
    run = repo / "audit" / "demo_run"
    write_log(run, [("prepare", 1), ("clean cf", 1), ("analysis", 3)] + ([("done", 3)] if analysed else []))
    (run / "analyze.py").write_text("print('pre-registered')\n")
    for condition, rows in (("cf", ROWS[:1]), ("plain", ROWS[1:])):
        folder = run / f"eval_{condition}"
        folder.mkdir()
        (folder / "tuned_interventions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return repo


# ---- run monitor -------------------------------------------------------------------

def test_date_lines_parse_with_short_numeric_zone():
    assert runs.parse_date("Sun Nov 15 17:20:56 +07 2026") == datetime(2026, 11, 15, 17, 20, 56, tzinfo=TZ)
    assert runs.parse_steps(">>> clean cf at Sun Nov 15 17:20:56 +07 2026\nother\n")[0][0] == "clean cf"


def test_current_step_estimate_comes_from_earlier_step_of_same_kind(tmp_path):
    write_log(tmp_path / "audit" / "r", [("prepare", 1), ("clean cf", 1), ("clean plain", 5)])
    status = runs.run_status(tmp_path / "audit" / "r" / "run.log", now=datetime(2026, 11, 15, 6, tzinfo=TZ))
    assert (status.current, status.elapsed_s, status.eta_s) == ("clean plain", 3600.0, 3 * 3600.0)
    assert not status.done


def test_step_without_earlier_kind_has_no_estimate_and_finished_runs_are_not_active(tmp_path):
    write_log(tmp_path / "audit" / "old", [("prepare", 1), ("finished with status 0", 2)])
    write_log(tmp_path / "audit" / "new", [("prepare", 1), ("interventions cf", 2)])
    status = runs.active_run(tmp_path, now=datetime(2026, 11, 15, 3, tzinfo=TZ))
    assert status.name == "new" and status.eta_s is None
    assert runs.run_status(tmp_path / "audit" / "old" / "run.log").done


TABLE = [
    Proc(1, 0, "Ss", "/sbin/launchd"),
    Proc(100, 1, "S", "caffeinate -i zsh audit/x/run.sh"),
    Proc(101, 100, "S", "/bin/zsh audit/x/run.sh"),
    Proc(102, 101, "R", ".venv/bin/python -u -m structured_llm.evaluate --adapter a"),
    Proc(103, 102, "S", "python -c resource_tracker"),
    Proc(200, 1, "S", "/usr/bin/vim notes.txt"),
]


def test_pause_and_resume_signal_the_whole_caffeinate_run_tree_only():
    sent = []
    runs.pause(TABLE, kill=lambda pid, sig: sent.append((pid, sig)))
    assert sent == [(pid, signal.SIGSTOP) for pid in (100, 101, 102, 103)]
    sent.clear()
    runs.resume(TABLE, kill=lambda pid, sig: sent.append((pid, sig)))
    assert {sig for _, sig in sent} == {signal.SIGCONT} and 200 not in {pid for pid, _ in sent}


def test_paused_state_is_read_from_the_job_process():
    stopped = [p if p.pid != 102 else Proc(102, 101, "T", p.command) for p in TABLE]
    assert runs.is_paused(runs.job_tree(stopped)) and not runs.is_paused(runs.job_tree(TABLE))
    assert runs.job_tree([p for p in TABLE if p.pid != 102]) == []


def test_rat_refuses_its_own_mlx_model_while_a_research_job_exists(tmp_path, monkeypatch):
    with pytest.raises(runs.ResearchJobRunning, match="research_mlx_job_running"):
        runs.ensure_no_research_mlx(TABLE)
    runs.ensure_no_research_mlx(TABLE[:2])

    from rat.engine import mlx_document_session
    model = tmp_path / "models--x" / "snapshots" / "abc"
    model.mkdir(parents=True)
    for name in ("config.json", "tokenizer.json", "model.safetensors"):
        (model / name).write_text("{}")
    monkeypatch.setattr(runs, "process_table", lambda: TABLE)
    monkeypatch.delenv("RAT_ALLOW_MLX_WITH_RESEARCH", raising=False)
    session = mlx_document_session.MLXDocumentSession(model)
    with pytest.raises(runs.ResearchJobRunning):
        session.load()
    assert not session.is_loaded


def test_tray_line_names_run_step_and_pause():
    status = runs.RunStatus("demo", "x", current="clean plain", elapsed_s=600, eta_s=1200)
    stopped = runs.job_tree([p if p.pid != 102 else Proc(102, 101, "T", p.command) for p in TABLE])
    assert runs.monitor_line(status, stopped) == "🧪 demo · clean plain · 10 ph · còn ~20 ph · ⏸"


# ---- blind labelling desk -----------------------------------------------------------

def test_desk_is_locked_until_the_preregistered_analysis_ran(tmp_path):
    repo = research_repo(tmp_path, analysed=False)
    with pytest.raises(labels.LabelDeskError, match="khóa"):
        labels.LabelDesk(repo, "demo_run", tmp_path / "labels")
    (repo / "audit" / "demo_run" / "analyze.py").unlink()
    assert not labels.analysis_done(repo / "audit" / "demo_run")[0]


def test_rows_are_pooled_and_shown_without_model_id_or_outcome(tmp_path):
    desk = labels.LabelDesk(research_repo(tmp_path), "demo_run", tmp_path / "labels")
    row = desk.next_row()
    shown = json.dumps(row)
    assert row["total"] == 2
    assert not {"outcome", "id", "flags", "source", "tokens"} & set(row)
    assert "eval_cf" not in shown and "eval_plain" not in shown and "follows" not in shown


def test_labels_are_saved_outside_the_repo_without_outcomes_and_newest_wins(tmp_path):
    repo = research_repo(tmp_path)
    desk = labels.LabelDesk(repo, "demo_run", tmp_path / "labels")
    first = desk.next_row()["key"]
    desk.record(first, "moved")
    desk.record(first, "other")
    assert desk.labels() == {first: "other"}
    stored = (tmp_path / "labels" / "demo_run.jsonl").read_text()
    assert "outcome" not in stored and "follows" not in stored
    assert desk.next_row()["key"] != first
    with pytest.raises(labels.LabelDeskError):
        desk.record(first, "maybe")
    with pytest.raises(labels.LabelDeskError, match="ngoài repo"):
        labels.LabelDesk(repo, "demo_run", repo / "labels")
    assert not list(repo.rglob("*labels*"))


def test_agreement_reports_kappa_and_confusion_against_automatic_outcomes(tmp_path):
    desk = labels.LabelDesk(research_repo(tmp_path), "demo_run", tmp_path / "labels")
    outcomes = desk.automatic_outcomes()
    for key in desk.order:
        desk.record(key, outcomes[key])
    report = desk.agreement()
    assert report["n"] == 2 and report["kappa"] == pytest.approx(1.0)
    follows, reverted = labels.LABELS.index("follows"), labels.LABELS.index("reverted")
    assert report["confusion"][follows][follows] == 1 and report["confusion"][reverted][reverted] == 1


def test_cohen_kappa_matches_hand_calculation():
    pairs = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]  # po=.75, pe=.5
    assert labels.cohen_kappa(pairs) == pytest.approx(0.5)
    assert labels.cohen_kappa([]) is None and labels.cohen_kappa([("a", "a")]) is None


# ---- paper desk ----------------------------------------------------------------------

def test_papers_are_copied_and_indexed_through_rats_indexer(tmp_path):
    source = tmp_path / "2401.00001.pdf"
    source.write_bytes(b"%PDF-1.4")
    (tmp_path / "notes.txt").write_text("x")
    indexed = []
    result = papers.add_papers([str(source), str(tmp_path / "notes.txt")], tmp_path / "papers",
                               index_file=lambda path: indexed.append(path) or True)
    assert indexed == [str(tmp_path / "papers" / "2401.00001.pdf")]
    assert [r["status"] for r in result] == ["đã lập chỉ mục", "bỏ qua: không phải tệp PDF"]


def test_answers_cite_the_pages_they_were_given(tmp_path):
    folder = tmp_path / "papers"
    folder.mkdir()
    for name in ("a.pdf", "b.pdf"):
        (folder / name).write_bytes(b"%PDF")
    pages = {"a.pdf": ["intro", "we evaluate on GSM8K test"], "b.pdf": ["unrelated"]}
    seen = {}

    def answer(text, question):
        seen["context"] = text
        return {"answer": "GSM8K", "engine": "fake"}

    result = papers.ask_papers(
        "evaluate GSM8K", folder,
        candidates=lambda q, ps: [p for p in ps if p.name == "a.pdf"],
        read_pages=lambda p: [{"page_num": i, "text_content": t} for i, t in enumerate(pages[p.name], 1)],
        score=lambda text, q, max_paragraphs: [(text, float("GSM8K" in text))],
        answer=answer)
    assert result["citations"] == [{"n": 1, "file": "a.pdf", "page": 2, "snippet": "we evaluate on GSM8K test"}]
    assert "[1] a.pdf, trang 2" in seen["context"] and result["papers"] == ["a.pdf"]
    with pytest.raises(ValueError, match="trống"):
        papers.ask_papers("x", tmp_path / "empty")


# ---- CLI views and CLI-to-UI ---------------------------------------------------------

def test_label_desk_works_headless_through_view_commands(tmp_path, monkeypatch):
    from rat.cli_views import run_view_command
    monkeypatch.setenv("RAT_RESEARCH_REPO", str(research_repo(tmp_path)))
    monkeypatch.setattr("rat.config.RAT_DIR", tmp_path / "state")
    listing = run_view_command(["label"])
    assert listing.blocks[1].data["rows"][0][:2] == ["demo_run", "mở"]
    spec = run_view_command(["label", "demo_run"])
    assert labels.WARNING in json.dumps(spec.to_dict(), ensure_ascii=False)
    buttons = spec.blocks[-1].data["commands"]
    assert [b["label"] for b in buttons][:7] == list(labels.LABELS)
    after = run_view_command(buttons[0]["argv"])
    assert after.blocks[1].data["title"] == "Hàng 2/2"
    assert run_view_command(["label", "demo_run", "--report"]).blocks[1].data["title"].startswith("Cohen's κ")


def test_json_envelope_and_exit_codes_for_agents(tmp_path, monkeypatch, capsys):
    from rat import cli_views
    monkeypatch.setenv("RAT_RESEARCH_REPO", str(research_repo(tmp_path, analysed=False)))
    monkeypatch.setattr("rat.config.RAT_DIR", tmp_path / "state")
    assert cli_views.run_view_command(["label", "demo_run"]).blocks[0].data["badge"] == "lỗi"
    assert cli_views.run_view_command(["nope"]).artifact_id == "cli:error"

    def call(*argv):
        code = cli_views.main([*argv, "--json"])
        envelope = json.loads(capsys.readouterr().out)
        assert envelope["schema"] == cli_views.SCHEMA and envelope["exit_code"] == code
        assert envelope["ok"] is (code == 0)
        return code, envelope

    code, envelope = call("runs", "list")
    assert code == 0 and envelope["data"]["runs"][0]["name"] == "demo_run"
    assert envelope["view"]["artifact_id"] == "cli:runs"
    code, envelope = call("label", "demo_run")
    assert code == cli_views.EXIT_REFUSED and "khóa" in envelope["data"]["error"]
    assert call("labels", "export", "demo_run")[0] == cli_views.EXIT_REFUSED
    assert call("runs", "bogus")[0] == cli_views.EXIT_USAGE
    assert call("tool", "run", "no_such_operation")[0] == cli_views.EXIT_FAILED


def test_pause_needs_the_active_run_name(tmp_path, monkeypatch):
    from rat import cli_views
    repo = research_repo(tmp_path)
    write_log(repo / "audit" / "live_run", [("clean cf", 1)])
    monkeypatch.setenv("RAT_RESEARCH_REPO", str(repo))
    table = [Proc(10, 1, "S", "caffeinate -i ./run.sh"), Proc(11, 10, "R", "python -m structured_llm.evaluate")]
    monkeypatch.setattr(runs, "process_table", lambda: table)
    sent = []
    monkeypatch.setattr(runs.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    for argv in (["runs", "pause"], ["runs", "pause", "demo_run"], ["runs", "resume", "nope"]):
        _, data, code = cli_views.run_command(argv)
        assert code == cli_views.EXIT_REFUSED and sent == [], argv
    assert "live_run" in cli_views.run_command(["runs", "pause", "demo_run"])[1]["error"]
    _, data, code = cli_views.run_command(["runs", "pause", "live_run"])
    assert code == 0 and data == {"action": "pause", "signal": "SIGSTOP", "pids": [10, 11]}
    assert sent == [(10, signal.SIGSTOP), (11, signal.SIGSTOP)]
    button = cli_views.run_command(["runs"])[0].blocks[-1].data["commands"][0]
    assert button["argv"] == ["runs", "pause", "live_run"]


def test_signal_run_refuses_without_an_active_run(tmp_path):
    repo = research_repo(tmp_path)
    with pytest.raises(runs.RunMismatch):
        runs.signal_run(repo, "demo_run", "pause", [], kill=lambda *a: None)


def test_estimate_comes_from_rows_written_against_the_manifest_limit(tmp_path):
    run = tmp_path / "audit" / "r"
    write_log(run, [("clean 50", 1), ("clean 50", 2)])
    out = run / "eval_50"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps({"limit": 500}))
    (out / "tuned.jsonl").write_text("{}\n" * 100)
    status = runs.run_status(run / "run.log", now=datetime(2026, 11, 15, 3, 0, tzinfo=TZ))
    assert status.progress == {"file": "eval_50/tuned.jsonl", "done": 100, "total": 500}
    assert status.eta_source == "progress" and status.eta_s == pytest.approx(4 * 3600)
    assert "100/500" in runs.monitor_line(status, [])
    (out / "tuned.jsonl").write_text("{}\n" * 3)  # too few rows: falls back to the step estimate
    assert runs.run_status(run / "run.log", now=datetime(2026, 11, 15, 3, 0, tzinfo=TZ)).eta_source == "steps"


def test_progress_eta_edges():
    assert runs.progress_eta(0, 500, 60) is None
    assert runs.progress_eta(500, 500, 60) is None
    assert runs.progress_eta(10, 20, 100) == pytest.approx(100)


def test_step_past_its_estimate_is_overdue_not_zero(tmp_path):
    run = tmp_path / "audit" / "r"
    write_log(run, [("clean 50", 1), ("clean 50", 2)])
    status = runs.run_status(run / "run.log", now=datetime(2026, 11, 15, 8, 0, tzinfo=TZ))
    assert status.overdue and status.eta_s is None
    assert "quá ước lượng" in runs.monitor_line(status, [])


def test_labels_export_and_report_give_raw_data(tmp_path, monkeypatch):
    from rat import cli_views
    monkeypatch.setenv("RAT_RESEARCH_REPO", str(research_repo(tmp_path)))
    monkeypatch.setattr("rat.config.RAT_DIR", tmp_path / "state")
    row = cli_views.run_command(["label", "demo_run"])[1]["row"]
    assert "outcome" not in row and "id" not in row
    cli_views.run_command(["label", "demo_run", "--set", row["key"], "follows"])
    _, exported, code = cli_views.run_command(["labels", "export", "demo_run"])
    assert code == 0 and exported["total"] == 2
    assert exported["latest"] == [{"key": row["key"], "label": "follows"}]
    assert exported["entries"][0]["label"] == "follows"
    _, report, _ = cli_views.run_command(["labels", "report", "demo_run"])
    assert report["n"] == 1 and len(report["confusion"]) == len(labels.LABELS)


def test_existing_registered_actions_run_headless():
    from rat.cli_views import run_view_command
    names = {row[1] for row in run_view_command(["tool", "list"]).blocks[1].data["rows"]}
    assert "calculate" in names
    spec = run_view_command(["tool", "run", "calculate", "--args", '{"expression": "45*3/2"}'])
    assert "67.5" in json.dumps(spec.to_dict())


def test_main_entry_routes_view_commands(tmp_path):
    env = {**os.environ, "RAT_RESEARCH_REPO": str(research_repo(tmp_path))}
    proc = subprocess.run([sys.executable, "main.py", "runs", "list", "--json"], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    envelope = json.loads(proc.stdout)
    assert envelope["schema"] == "rat.cli/1" and envelope["view"]["title"] == "Các run"


def test_desk_command_text_is_parsed_into_argv():
    from rat.ui.quick_pdf_controller import QuickPDFController
    assert QuickPDFController.parse_cli_text('/rat papers ask "what is x"') == ["papers", "ask", "what is x"]
    assert QuickPDFController.parse_cli_text('/rat "unclosed') == []
