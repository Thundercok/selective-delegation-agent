"""
tests/test_diagnostics_command.py — Verification of RAT doctor diagnostic checks.
"""
from __future__ import annotations

import pytest

from rat.os.diagnostics import collect_system_diagnostics


def test_collect_system_diagnostics_schema():
    report = collect_system_diagnostics()

    assert "timestamp" in report
    assert report["overall_status"] in ("PASS", "WARN", "FAIL")
    assert report["exit_code"] in (0, 1)

    checks = report["checks"]
    assert "environment" in checks
    assert "database" in checks
    assert "configuration" in checks
    assert "models" in checks
    assert "permissions" in checks

    env = checks["environment"]
    assert env["status"] in ("PASS", "WARN", "FAIL")
    assert "python_version" in env["details"]

    db = checks["database"]
    assert db["status"] in ("PASS", "WARN", "FAIL")
    assert "path" in db["details"]


def test_diagnostics_cli_execution():
    from rat.cli import cmd_doctor

    code = cmd_doctor(as_json=True)
    assert code in (0, 1)


READY = {"translation_ready": True, "embedding_bundled": True, "mlx_installed": True}


def test_model_asset_problems_empty_when_everything_present():
    from rat.os.diagnostics import model_asset_problems

    assert model_asset_problems(READY) == []


def test_model_asset_problems_names_each_missing_asset():
    from rat.os.diagnostics import model_asset_problems

    problems = " ".join(model_asset_problems({**READY, "translation_ready": False, "embedding_bundled": False}))
    assert "prepare_rat_translation_models.py" in problems
    assert "prepare_rat_embedding_model.py" in problems


def test_missing_translation_models_turn_doctor_to_warn(monkeypatch):
    import rat.os.diagnostics as diag

    monkeypatch.setattr(diag, "local_model_assets", lambda: {**READY, "translation_ready": False})
    models = diag.collect_system_diagnostics()["checks"]["models"]
    assert models["status"] == "WARN"
    assert "Translation models missing" in models["message"]


def test_dangling_model_symlink_is_not_ready(tmp_path):
    """The models were once symlinks into another repo; when it was cleaned, translation stopped silently."""
    import json
    from rat.engine.local_translation import is_local_models_ready

    (tmp_path / "manifest.json").write_text(json.dumps({"models": {"en-vi": {}, "vi-en": {}}}))
    for pair in ("en-vi", "vi-en"):
        (tmp_path / pair / "model").mkdir(parents=True)
        for rel in ("sentencepiece.model", "model/config.json", "model/model.bin", "model/shared_vocabulary.json"):
            (tmp_path / pair / rel).write_bytes(b"x")
    assert is_local_models_ready(tmp_path)

    target = tmp_path / "en-vi" / "model" / "model.bin"
    target.unlink()
    target.symlink_to(tmp_path / "gone" / "model.bin")
    assert not is_local_models_ready(tmp_path)


def test_accessibility_message_silent_when_trusted():
    from rat.os.diagnostics import accessibility_message

    assert accessibility_message(True, True, "⌥⇧R") is None
    assert accessibility_message(True, False, "⌥⇧R") is None


def test_accessibility_message_does_not_blame_hotkeys_when_native_helper_runs():
    from rat.os.diagnostics import accessibility_message

    message = accessibility_message(False, True, "⌥⇧R")
    assert "Hotkeys work through the native helper" in message
    assert "⌥⇧R" in message and "2 minutes" in message


def test_accessibility_message_names_hotkeys_without_native_helper():
    from rat.os.diagnostics import accessibility_message

    assert "Global hotkeys need Accessibility" in accessibility_message(False, False, "⌥⇧R")
