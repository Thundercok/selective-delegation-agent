# PyInstaller spec for RAT.app (Apple Silicon, onedir bundle).
# Build with: zsh tools/build_app.sh   (output: dist/RAT.app)
#
# Runtime code already looks for data under sys._MEIPASS/rat/..., so every
# data folder keeps its repo-relative path inside the bundle.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).parent

datas = [
    (str(ROOT / "rat/ui/quick"), "rat/ui/quick"),
    (str(ROOT / "rat/assets"), "rat/assets"),
    (str(ROOT / "rat/astrology/ephemeris"), "rat/astrology/ephemeris"),
    (str(ROOT / "rat/engine/snapshot.schema.json"), "rat/engine"),
    (str(ROOT / "tools/rat_translation_models.lock.json"), "tools"),
    (str(ROOT / "tools/rat_embedding_model.lock.json"), "tools"),
]
datas += collect_data_files("mlx")          # mlx.metallib: Metal kernels, loaded at runtime
datas += collect_data_files("mlx_lm")

# Native helpers (hotkey, Apple translate, spider crawler) stay executables in rat/bin.
binaries = [(str(p), "rat/bin") for p in sorted((ROOT / "rat/bin").iterdir()) if p.is_file()]
binaries += collect_dynamic_libs("mlx")

hiddenimports = (
    collect_submodules("rat")
    + collect_submodules("document_intake")
    + collect_submodules("mlx_lm.models")   # model classes are imported by name from config.json
)

# TODO(human): decide what stays out of the shipped bundle.
EXCLUDES = [
    "tkinter",
    "pytest",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RAT",
    console=False,
    target_arch="arm64",
    codesign_identity=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="RAT")
app = BUNDLE(
    coll,
    name="RAT.app",
    bundle_identifier="io.github.thundercok.rat",
    info_plist={
        "CFBundleDisplayName": "RAT",
        "CFBundleShortVersionString": "0.1.0",
        "LSMinimumSystemVersion": "13.0",
        "LSUIElement": True,                 # resident app: tray + hotkey, no Dock icon
        "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription": "RAT mở và điều khiển ứng dụng khi bạn yêu cầu.",
    },
)
