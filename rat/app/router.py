"""
rat.app.router — Application mode routing and dispatching.

Decouples command line interpretation and resident/GUI dispatching from
the primary interpreter bootstrap.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from typing import Sequence

logger = logging.getLogger("rat.app.router")


def cli_main() -> None:
    """Delegate to CLI parser and handlers."""
    from rat.cli import main as run_cli
    run_cli()


def run_resident_app(mode: str = "finder", *, reasoning_engine=None, allow_synthetic_policy=False) -> None:
    """Launch resident macOS background/desktop application with crash shielding."""
    from rat.os.crash_shield import install_crash_shield
    install_crash_shield()
    from rat.os.app import run_resident_app as launch
    if reasoning_engine is None:
        launch(mode=mode)
    else:
        launch(mode=mode, reasoning_engine=reasoning_engine,
               allow_synthetic_policy=allow_synthetic_policy)


def _get_cli_runner():
    main_mod = sys.modules.get("rat.main")
    return getattr(main_mod, "cli_main", cli_main) if main_mod else cli_main


def _get_resident_runner():
    main_mod = sys.modules.get("rat.main")
    return getattr(main_mod, "run_resident_app", run_resident_app) if main_mod else run_resident_app


def route_request(args: Sequence[str] | None = None) -> None:
    """
    Route an incoming invocation to the appropriate subsystem:
    - Diagnostics session
    - Quick PDF or Quick Desk view
    - Standalone Astrology window
    - CLI command (search, index, doctor, status, etc.)
    - Shell integration or LaunchAgent daemon installer
    - Resident GUI modes (daemon, spotlight, widget, schedule, finder)
    - Direct single-action CLI query (math AST, campus room, agenda)
    - Default fallback: Unified Qt Quick Desk
    """
    if args is None:
        args = sys.argv[1:]

    run_cli_handler = _get_cli_runner()
    run_resident = _get_resident_runner()

    if args:
        cmd = args[0]
        if cmd == "--diagnostics":
            from rat.os.diagnostics import run_session
            raise SystemExit(run_session(list(args[1:])))
        elif cmd == "quick-pdf":
            from rat.ui.quick_app import main as quick_pdf_main
            raise SystemExit(quick_pdf_main(list(args[1:])))
        elif cmd.lower().endswith(".pdf"):
            from rat.ui.quick_app import main as quick_pdf_main
            raise SystemExit(quick_pdf_main(list(args)))
        elif cmd in ("search", "index", "status", "ask", "ask-file", "dedup", "review", "doctor", "--help", "-h"):
            run_cli_handler()
            return
        elif cmd in ("runs", "papers", "label", "labels", "tool"):
            from rat.cli_views import main as view_main
            raise SystemExit(view_main(list(args)))
        elif cmd == "mcp":
            from rat.mcp_server import main as mcp_main
            raise SystemExit(mcp_main(list(args[1:])))
        elif cmd == "native-sync":
            from rat.native_bridge import main as native_sync_main
            raise SystemExit(native_sync_main(list(args[1:])))
        elif cmd == "ui":
            # CLI-to-UI: open the desk on a view command's ViewSpec, e.g. `rat ui runs`.
            import shlex
            from rat.ui.quick_app import main as quick_main
            raise SystemExit(quick_main(["--cli", shlex.join(args[1:]) or "runs"]))
        elif cmd in ("init-shell", "shell"):
            from rat.os.shell_integration import generate_shell_init_script
            print(generate_shell_init_script())
            return
        elif cmd == "install-shell":
            from rat.os.shell_integration import install_to_user_zshrc
            ok = install_to_user_zshrc()
            print("✓ Đã cài đặt tích hợp lệnh 'rat' vào ~/.zshrc!" if ok else "⚠️ Không thể ghi vào ~/.zshrc")
            return
        elif cmd in ("install-daemon", "install-service"):
            from rat.os.daemon import install_launch_agent
            ok = install_launch_agent()
            print("✓ Đã cài đặt LaunchAgent tự động khởi động cùng macOS!" if ok else "⚠️ Cài đặt LaunchAgent thất bại")
            return
        elif cmd in ("uninstall-daemon", "uninstall-service"):
            from rat.os.daemon import uninstall_launch_agent
            ok = uninstall_launch_agent()
            print("✓ Đã gỡ bỏ LaunchAgent khỏi macOS!" if ok else "⚠️ Gỡ bỏ LaunchAgent thất bại")
            return
        elif cmd in ("--daemon", "-d"):
            run_resident(mode="daemon")
            return
        elif cmd in ("spotlight", "widgets", "omnibar"):
            run_resident(mode="spotlight")
            return
        elif cmd.startswith("--mode="):
            target_mode = cmd.split("=", 1)[1]
            if target_mode in ("quick", "quick-pdf"):
                from rat.ui.quick_app import main as quick_main
                raise SystemExit(quick_main(list(args[1:])))
            else:
                run_resident(mode=target_mode)
                return
        elif cmd == "--mode" and len(args) > 1:
            target_mode = args[1]
            if target_mode in ("quick", "quick-pdf"):
                from rat.ui.quick_app import main as quick_main
                raise SystemExit(quick_main(list(args[2:])))
            else:
                run_resident(mode=target_mode)
                return
        elif cmd in ("widget", "mini", "claude"):
            run_resident(mode="widget")
            return
        elif cmd in ("schedule", "tkb", "lich"):
            if len(args) > 1 and args[1] in ("--widget", "-w", "widget"):
                run_resident(mode="widget")
            else:
                run_resident(mode="schedule")
            return
        elif cmd == "finder":
            run_resident(mode="finder")
            return
        elif not cmd.startswith("-"):
            # 1-Action Direct CLI Resolver for Math, Campus Room, or Schedule queries
            query = " ".join(args).strip()

            # 1. Quick Math via AST safe_calculate
            calc_cand = re.sub(r"^(?:tính|tinh|calc|calculate|\=)\s*", "", query, flags=re.I).strip()
            if re.search(r"\d", calc_cand) and any(op in calc_cand for op in ["+", "*", "/", "%", "^", " - "]):
                try:
                    from reasoning.reasoning_strategies import safe_calculate
                    res = safe_calculate(calc_cand)
                    if res and "Lỗi" not in res and res != "None":
                        print(f"🧮 Kết quả tính toán: {res}")
                        return
                except Exception:
                    pass

            # Fallback to semantic file search in CLI
            run_cli_handler()
            return

    # Primary unified entry point: summon unified RAT Qt Quick Desk
    from rat.ui.quick_app import main as quick_main
    raise SystemExit(quick_main(list(args)))
