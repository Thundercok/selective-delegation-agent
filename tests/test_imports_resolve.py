"""Every first-party import in the shipped packages must point at a module that exists.

Importing each module (the first test) catches a broken top-level import, but not one
hidden inside a function body: `from research_scoring import ...` sat inside
`extract_answer()` for weeks after the module was deleted and only failed when called.
The second test therefore reads the source and checks every import statement, wherever it is.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import pkgutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("rat", "reasoning", "document_intake")

# First-party top-level names: a dangling import of one of these is always our bug.
FIRST_PARTY_TOP = {p.name for p in ROOT.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
FIRST_PARTY_TOP |= {p.stem for p in ROOT.glob("*.py")}
# Names that were deleted on purpose: any import of them is a leftover.
REMOVED_TOP = {"research_scoring"}


def _source_files() -> list[Path]:
    files: list[Path] = []
    for pkg in PACKAGES:
        files.extend(sorted((ROOT / pkg).rglob("*.py")))
    return files


def _module_names() -> list[str]:
    names: list[str] = []
    for pkg in PACKAGES:
        mod = importlib.import_module(pkg)
        for info in pkgutil.walk_packages(mod.__path__, f"{pkg}."):
            if not info.name.endswith(".__main__"):
                names.append(info.name)
    return names


@pytest.mark.parametrize("name", _module_names())
def test_module_imports(name: str) -> None:
    importlib.import_module(name)


def _dangling_imports(path: Path) -> list[str]:
    rel = path.relative_to(ROOT)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets = [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            targets = [(node.module, node.lineno)]
            # `from pkg import submodule` is fine only if the name is an attribute or a module.
            for alias in node.names:
                full = f"{node.module}.{alias.name}"
                top = node.module.split(".")[0]
                if top in FIRST_PARTY_TOP and importlib.util.find_spec(node.module) is not None:
                    mod = importlib.import_module(node.module)
                    if not hasattr(mod, alias.name) and importlib.util.find_spec(full) is None:
                        problems.append(f"{rel}:{node.lineno} cannot import name {alias.name!r} from {node.module}")
        else:
            continue
        for module, lineno in targets:
            top = module.split(".")[0]
            if top in REMOVED_TOP:
                problems.append(f"{rel}:{lineno} imports removed module {module}")
            elif top in FIRST_PARTY_TOP:
                try:
                    found = importlib.util.find_spec(module) is not None
                except ModuleNotFoundError:
                    found = False
                if not found:
                    problems.append(f"{rel}:{lineno} imports missing module {module}")
    return problems


def test_no_dangling_first_party_imports_anywhere_in_source() -> None:
    problems: list[str] = []
    for path in _source_files():
        problems.extend(_dangling_imports(path))
    assert not problems, "dangling imports:\n" + "\n".join(problems)
