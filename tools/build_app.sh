#!/bin/zsh
# Build dist/RAT.app with PyInstaller. Ad-hoc signed only: fine for running on
# this Mac or a test machine you install by hand, not for public download
# (that needs a Developer ID certificate and notarization).
set -euo pipefail
cd "${0:A:h}/.."

.venv/bin/python -c "from rat.engine.local_translation import find_translation_directory as f, is_local_models_ready as r; import sys; sys.exit(0 if r(f()) else 1)" \
  || { echo "Thiếu model dịch: chạy tools/prepare_rat_translation_models.py trước." >&2; exit 1; }

uv run --group dev pyinstaller --noconfirm --clean \
  --workpath build/pyinstaller --distpath dist packaging/RAT.spec

codesign --force --deep --sign - dist/RAT.app
echo "Đã build: dist/RAT.app ($(du -sh dist/RAT.app | cut -f1))"
