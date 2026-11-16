"""CLI commands that return a ViewSpec, so one command gives a terminal view and a desk view.

Each command builds a ``ViewSpec`` from the kernel's block vocabulary (summary, table,
details, actions). The terminal prints it with rich, ``--json`` prints the dict, and
the Qt Quick desk renders the same dict (``CliView.qml``). Buttons are ``actions``
blocks whose ``commands`` hold the argv of the next command, so a CLI command becomes
an interactive desk view without hand-written UI. ``drop_argv`` lets the desk append
dropped file paths to a command; ``refresh_seconds`` on the first summary re-runs it.

These specs are not artifact views: ``artifact_id`` is ``cli:<command>`` and the
registry's action validation does not apply.

For agents, ``--json`` prints one envelope ``{"schema": "rat.cli/1", "command", "ok",
"exit_code", "data", "view"}``. ``data`` holds the command's raw result and is the part
to parse; ``view`` is the ViewSpec for display. Commands never prompt. Exit codes: 0 ok,
1 failed, 2 bad usage, 3 refused on purpose (label desk locked, wrong run, MLX guard).
"""
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from rat.kernel.view_spec import ViewBlock, ViewSpec

VIEW_COMMANDS = ("runs", "papers", "label", "labels", "tool")
SCHEMA = "rat.cli/1"
EXIT_OK, EXIT_FAILED, EXIT_USAGE, EXIT_REFUSED = 0, 1, 2, 3
Result = Tuple[ViewSpec, Any]


class Refused(RuntimeError):
    """A deliberate refusal: the command was understood but must not run now."""


def _spec(command: str, title: str, blocks: List[ViewBlock]) -> ViewSpec:
    return ViewSpec(1, f"cli:{command}", 1, title=title, blocks=blocks)


def _commands(*items, drop_argv=None) -> ViewBlock:
    data = {"commands": [{"label": label, "argv": list(argv)} for label, argv in items]}
    if drop_argv:
        data["drop_argv"] = list(drop_argv)
    return ViewBlock("actions", data)


def _duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    minutes = int(seconds // 60)
    return f"{minutes // 60} giờ {minutes % 60:02d} phút" if minutes >= 60 else f"{minutes} phút"


# ---- runs ------------------------------------------------------------------------

def view_runs(args) -> Result:
    from rat.research import research_repo
    from rat.research import runs
    repo = research_repo()
    if args.action in ("pause", "resume"):
        if not args.run:
            raise Refused(f"Ghi tên run: rat runs {args.action} <run>. Không ghi tên thì không gửi tín hiệu, "
                          "để không dừng nhầm một run khác.")
        try:
            sent = runs.signal_run(repo, args.run, args.action)
        except runs.RunMismatch as error:
            raise Refused(str(error)) from error
        verb = "Tạm dừng" if args.action == "pause" else "Tiếp tục"
        text = (f"Đã gửi {'SIGSTOP' if args.action == 'pause' else 'SIGCONT'} tới {len(sent)} tiến trình: "
                + ", ".join(map(str, sent))) if sent else "Không có job MLX nào đang chạy."
        if sent and args.action == "pause":
            text += "\nSIGSTOP giải phóng GPU/CPU, không giải phóng RAM của job."
        return _spec("runs", f"{verb} run", [ViewBlock("summary", {"title": f"{verb} job MLX", "text": text}),
                                             _commands(("Xem run", ["runs"]))]), {
            "action": args.action, "signal": "SIGSTOP" if args.action == "pause" else "SIGCONT", "pids": sent}
    if args.action == "list":
        rows, listed = [], []
        for log in runs.list_runs(repo):
            status = runs.run_status(log)
            last = status.steps[-1]["name"] if status.steps else "—"
            rows.append([status.name, "xong" if status.done else last, str(len(status.steps))])
            listed.append({"name": status.name, "done": status.done, "last_step": status.steps[-1]["name"]
                           if status.steps else None, "steps": len(status.steps), "log_path": status.log_path})
        return _spec("runs", "Các run", [
            ViewBlock("summary", {"title": "Các run trong audit/", "text": f"{len(rows)} run · {repo}"}),
            ViewBlock("table", {"headers": ["Run", "Bước cuối", "Số bước"], "rows": rows})]), {
            "repo": str(repo), "runs": listed}
    status = runs.active_run(repo)
    tree = runs.job_tree(runs.process_table())
    paused = runs.is_paused(tree)
    job_text = ("Không thấy job MLX nào." if not tree else
                f"Job MLX: {len(tree)} tiến trình · {'ĐANG TẠM DỪNG' if paused else 'đang chạy'}")
    if status is None:
        blocks = [ViewBlock("summary", {"title": "Không có run đang chạy", "text": job_text,
                                        "refresh_seconds": 30})]
    else:
        if status.eta_source == "progress":
            eta = (f"{status.progress['done']}/{status.progress['total']} hàng · ước còn "
                   f"{_duration(status.eta_s)} (theo tiến độ {status.progress['file']})")
        elif status.eta_source == "steps":
            eta = f"ước còn {_duration(status.eta_s)} (từ bước cùng loại trước đó)"
        elif status.overdue:
            eta = "đã quá thời lượng của bước cùng loại trước đó; chưa ước được"
        else:
            eta = "chưa ước được (chưa có tiến độ hay bước cùng loại đã xong)"
        blocks = [
            ViewBlock("summary", {"title": f"{status.name} · {status.current}",
                                  "text": f"Đã chạy {_duration(status.elapsed_s)} · {eta}\n{job_text}",
                                  "badge": "tạm dừng" if paused else "đang chạy", "refresh_seconds": 30}),
            ViewBlock("table", {"headers": ["Bước", "Bắt đầu", "Thời lượng"],
                                "rows": [[s["name"], s["started"], _duration(s["duration_s"])]
                                         for s in status.steps]}),
        ]
    if tree and status is not None:
        blocks.append(_commands(("Tiếp tục job", ["runs", "resume", status.name]) if paused
                                else ("Tạm dừng job", ["runs", "pause", status.name])))
    return _spec("runs", "Theo dõi run", blocks), {
        "repo": str(repo), "active": asdict(status) if status else None, "paused": paused,
        "jobs": [{"pid": p.pid, "ppid": p.ppid, "stat": p.stat, "command": p.command} for p in tree]}


# ---- papers ----------------------------------------------------------------------

def view_papers(args) -> Result:
    from rat.research import papers
    drop = ["papers", "add"]
    if args.action == "add":
        added = papers.add_papers(args.items)
        return _spec("papers", "Thêm bài báo", [
            ViewBlock("summary", {"title": "Thêm bài báo", "text": f"{len(added)} tệp"}),
            ViewBlock("table", {"headers": ["Tệp", "Trạng thái"], "rows": [[a["file"], a["status"]] for a in added]}),
            _commands(("Danh sách bài", ["papers"]), drop_argv=drop)]), {"added": added}
    if args.action == "ask":
        question = " ".join(args.items).strip()
        if not question:
            raise ValueError("Cần câu hỏi: rat papers ask \"...\"")
        result = papers.ask_papers(question)
        return _spec("papers", f"Hỏi bài báo · {question}", [
            ViewBlock("summary", {"title": question, "text": result["answer"], "badge": result["engine"]}),
            ViewBlock("table", {"headers": ["#", "Bài", "Trang", "Đoạn trích"],
                                "rows": [[c["n"], c["file"], c["page"], c["snippet"]] for c in result["citations"]]}),
            ViewBlock("details", {"title": "Bài đã đọc", "content": "\n".join(result["papers"])}),
            _commands(("Danh sách bài", ["papers"]), drop_argv=drop)]), {"question": question, **result}
    listed = papers.list_papers()
    return _spec("papers", "Bàn bài báo", [
        ViewBlock("summary", {"title": "Bàn bài báo", "text": f"{len(listed)} PDF trong {papers.papers_dir()}. "
                              "Thả PDF vào đây để thêm; hỏi bằng: /rat papers ask <câu hỏi>"}),
        ViewBlock("table", {"headers": ["Tệp"], "rows": [[p.name] for p in listed]}),
        _commands(drop_argv=drop)]), {"dir": str(papers.papers_dir()), "papers": [p.name for p in listed]}


# ---- blind labels ----------------------------------------------------------------

def view_label(args) -> Result:
    from rat.config import RAT_DIR
    from rat.research import labels, research_repo
    repo = research_repo()
    warning = ViewBlock("summary", {"title": "Cảnh báo", "text": labels.WARNING, "badge": "mù"})
    if not args.run:
        rows = []
        for run_dir in sorted((repo / "audit").glob("*")):
            if any(run_dir.glob("eval_*/*_interventions.jsonl")):
                ok, reason = labels.analysis_done(run_dir)
                rows.append([run_dir.name, "mở" if ok else "khóa", reason])
        return _spec("label", "Bàn gán nhãn mù", [
            warning, ViewBlock("table", {"headers": ["Run", "Trạng thái", "Lý do"], "rows": rows}),
            _commands(*[(f"Mở {r[0]}", ["label", r[0]]) for r in rows if r[1] == "mở"])]), {
            "runs": [{"run": r[0], "open": r[1] == "mở", "reason": r[2]} for r in rows]}
    try:
        desk = labels.LabelDesk(repo, args.run, RAT_DIR / "labels")
    except labels.LabelDeskError as error:
        raise Refused(str(error)) from error
    if args.set:
        desk.record(args.set[0], args.set[1])
    if args.report:
        report = desk.agreement()
        kappa = "—" if report["kappa"] is None else f"{report['kappa']:.3f}"
        agree = "—" if report["observed_agreement"] is None else f"{report['observed_agreement']:.1%}"
        return _spec("label", f"Đồng thuận · {args.run}", [
            warning,
            ViewBlock("summary", {"title": f"Cohen's κ = {kappa}",
                                  "text": f"{report['n']}/{report['total']} hàng đã gán · khớp thô {agree}. "
                                          "Hàng: nhãn người; cột: outcome tự động."}),
            ViewBlock("table", {"headers": ["người \\ tự động", *labels.LABELS],
                                "rows": [[h, *row] for h, row in zip(labels.LABELS, report["confusion"])]}),
            _commands(("Gán tiếp", ["label", args.run]))]), {"run": args.run, "labels": list(labels.LABELS), **report}
    row = desk.next_row()
    if row is None:
        return _spec("label", f"Gán nhãn · {args.run}", [
            warning, ViewBlock("summary", {"title": "Đã gán hết", "text": f"{len(desk.order)} hàng."}),
            _commands(("Xem κ và ma trận nhầm lẫn", ["label", args.run, "--report"]))]), {
            "run": args.run, "row": None, "total": len(desk.order)}
    return _spec("label", f"Gán nhãn · {args.run}", [
        warning,
        ViewBlock("summary", {"title": f"Hàng {row['position']}/{row['total']}",
                              "text": f"cũ {row['old']} → mới {row['new']} · nếu theo bước sửa: {row['expected']} "
                                      f"· đáp án gốc: {row['original']}"}),
        ViewBlock("details", {"title": "Tiền tố đã sửa", "content": row["prefix"] or ""}),
        ViewBlock("details", {"title": "Phần mô hình viết tiếp", "content": row["continuation"] or ""}),
        _commands(*[(label, ["label", args.run, "--set", row["key"], label]) for label in labels.LABELS],
                  ("Xem κ", ["label", args.run, "--report"])),
    ]), {"run": args.run, "row": row, "labels": list(labels.LABELS)}


def view_labels(args) -> Result:
    """Agent-facing label commands: ``labels`` lists runs, ``labels export|report <run>``."""
    if args.action == "list" or not args.run:
        return view_label(argparse.Namespace(run=None, set=None, report=False))
    if args.action == "report":
        return view_label(argparse.Namespace(run=args.run, set=None, report=True))
    from rat.config import RAT_DIR
    from rat.research import labels, research_repo
    try:
        desk = labels.LabelDesk(research_repo(), args.run, RAT_DIR / "labels")
    except labels.LabelDeskError as error:
        raise Refused(str(error)) from error
    entries = []
    if desk.store.is_file():
        entries = [json.loads(line) for line in desk.store.read_text().splitlines() if line.strip()]
    latest = desk.labels()
    return _spec("labels", f"Xuất nhãn · {args.run}", [
        ViewBlock("summary", {"title": f"Xuất nhãn · {args.run}",
                              "text": f"{len(latest)}/{len(desk.order)} hàng đã gán · {desk.store}"})]), {
        "run": args.run, "store": str(desk.store), "total": len(desk.order),
        "latest": [{"key": k, "label": v} for k, v in latest.items()], "entries": entries}


# ---- registered operations (RAT's existing actions) -------------------------------

def view_tool(args) -> Result:
    from rat.kernel.capabilities import build_default_registry
    registry = build_default_registry()
    if args.action == "list" or not args.operation:
        rows = [[cap.name, op.name, op.description.split(". ")[0][:120]]
                for cap in registry.list_capabilities() for op in cap.operations.values()]
        return _spec("tool", "Thao tác của RAT", [
            ViewBlock("summary", {"title": "Thao tác đã đăng ký",
                                  "text": f"{len(rows)} thao tác. Chạy: rat tool run <tên> --args '{{...}}'"}),
            ViewBlock("table", {"headers": ["Nhóm", "Thao tác", "Mô tả"], "rows": rows})]), {
            "operations": [{"capability": r[0], "operation": r[1], "description": r[2]} for r in rows]}
    from rat.kernel.contracts import ArtifactStore
    from rat.kernel.dispatcher import ActionDispatcher
    from rat.kernel.view_spec import StandardViewProvider
    result = ActionDispatcher(registry, ArtifactStore()).execute_operation(args.operation, json.loads(args.args or "{}"))
    data = {"operation": args.operation, "status": result.status, "result": result.result, "error": result.error}
    if result.status not in ("success", "needs_input"):
        raise RuntimeError(result.error or f"{args.operation}: {result.status}")
    if result.artifact is not None and result.status == "success":
        return StandardViewProvider(registry).provide_view(result.artifact), data
    text = result.error or json.dumps(result.result, ensure_ascii=False, default=str)
    if result.status == "needs_input" and result.input_request is not None:
        text = f"{result.input_request.prompt} Thiếu: {', '.join(result.input_request.missing_fields or [])}"
    return _spec("tool", args.operation, [ViewBlock("summary", {"title": args.operation, "text": text,
                                                                "badge": result.status})]), data


# ---- parsing, running, rendering ---------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rat", add_help=True)
    parser.add_argument("--json", action="store_true", help="In ViewSpec dạng JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("runs", help="Theo dõi run nghiên cứu; tạm dừng/tiếp tục job MLX")
    p.add_argument("action", nargs="?", default="status", choices=("status", "list", "pause", "resume"))
    p.add_argument("run", nargs="?", help="Bắt buộc với pause/resume: chỉ gửi tín hiệu nếu đây là run đang chạy")
    p = sub.add_parser("papers", help="Bàn bài báo: thêm PDF, hỏi kèm trích dẫn trang")
    p.add_argument("action", nargs="?", default="list", choices=("list", "add", "ask"))
    p.add_argument("items", nargs="*")
    p = sub.add_parser("label", help="Bàn gán nhãn mù cho tệp interventions")
    p.add_argument("run", nargs="?")
    p.add_argument("--set", nargs=2, metavar=("KEY", "LABEL"))
    p.add_argument("--report", action="store_true", help="Cohen's κ và ma trận nhầm lẫn")
    p = sub.add_parser("labels", help="Cho agent: liệt kê run, xuất nhãn, báo cáo κ")
    p.add_argument("action", nargs="?", default="list", choices=("list", "export", "report"))
    p.add_argument("run", nargs="?")
    p = sub.add_parser("tool", help="Chạy một thao tác đã đăng ký của RAT")
    p.add_argument("action", nargs="?", default="list", choices=("list", "run"))
    p.add_argument("operation", nargs="?")
    p.add_argument("--args", help="Tham số JSON")
    return parser


BUILDERS = {"runs": view_runs, "papers": view_papers, "label": view_label, "labels": view_labels,
            "tool": view_tool}


def _failure(command: str, title: str, text: str) -> ViewSpec:
    return _spec(command, title, [ViewBlock("summary", {"title": title, "text": text, "badge": "lỗi"})])


def run_command(argv: Sequence[str]) -> Tuple[ViewSpec, Any, int]:
    """Run one view command and return (view, data, exit code); it never raises or prompts."""
    argv = list(argv)
    try:
        args = build_parser().parse_args(argv)
    except SystemExit:
        text = "rat " + shlex.join(argv) + "\nDùng: " + ", ".join(VIEW_COMMANDS)
        return _failure("error", "Lệnh không hợp lệ", text), {"error": text}, EXIT_USAGE
    try:
        spec, data = BUILDERS[args.command](args)
        return spec, data, EXIT_OK
    except Refused as error:
        return _failure(args.command, "Bị từ chối", str(error)), {"error": str(error)}, EXIT_REFUSED
    except (ValueError, RuntimeError, OSError) as error:
        from rat.research.runs import ResearchJobRunning
        code = EXIT_REFUSED if isinstance(error, ResearchJobRunning) else EXIT_FAILED
        return _failure(args.command, "Không chạy được", str(error)), {"error": str(error)}, code


def run_view_command(argv: Sequence[str]) -> ViewSpec:
    """The view alone, for the desk; errors become a summary view."""
    return run_command(argv)[0]


def render_console(spec: ViewSpec, console=None) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = console or Console()
    for block in spec.blocks:
        data = block.data
        if block.type == "summary":
            title = data.get("title", "") + (f"  [{data['badge']}]" if data.get("badge") else "")
            console.print(Panel(data.get("text", ""), title=title, title_align="left"), markup=False)
        elif block.type in ("table", "details") and data.get("headers", data.get("table_headers")):
            table = Table(*map(str, data.get("headers", data.get("table_headers"))), title=data.get("title"))
            for row in data.get("rows", data.get("table_rows", [])):
                table.add_row(*(str(cell) for cell in row))
            console.print(table)
        elif block.type == "details":
            console.print(Panel(str(data.get("content", "")), title=data.get("title", ""), title_align="left"),
                          markup=False)
        elif block.type == "actions" and data.get("commands"):
            for command in data["commands"]:
                console.print(f"  → {command['label']}: rat {shlex.join(command['argv'])}", markup=False,
                              soft_wrap=True)
            if data.get("drop_argv"):
                console.print(f"  → thả tệp: rat {shlex.join(data['drop_argv'])} <tệp...>", markup=False)


def main(argv: Sequence[str]) -> int:
    argv = list(argv)
    as_json = "--json" in argv
    rest = [a for a in argv if a != "--json"]
    if not as_json and any(a in ("-h", "--help") for a in rest):
        try:
            build_parser().parse_args(rest)
        except SystemExit as stop:
            return int(stop.code or 0)
    spec, data, code = run_command(rest)
    if as_json:
        envelope = {"schema": SCHEMA, "command": rest[0] if rest else None, "argv": rest,
                    "ok": code == EXIT_OK, "exit_code": code, "data": data, "view": spec.to_dict()}
        print(json.dumps(envelope, ensure_ascii=False, indent=2, default=str))
    else:
        render_console(spec)
    return code
