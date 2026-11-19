# Selective Delegation Agent

<p align="center">
  <strong>A standalone local-first macOS assistant and document intelligence toolkit, with a desktop interface, headless CLI, and optional MCP integration.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat-square" alt="Python 3.11+" /></a>
  <a href="https://developer.apple.com/metal/"><img src="https://img.shields.io/badge/Platform-macOS%20(Apple%20Silicon)-black?style=flat-square" alt="macOS Apple Silicon" /></a>
  <a href="https://www.riverbankcomputing.com/software/pyqt/"><img src="https://img.shields.io/badge/UI-PyQt6%20%2F%20Qt%20Quick-41CD52.svg?style=flat-square" alt="PyQt6" /></a>
  <a href="https://github.com/ml-explore/mlx"><img src="https://img.shields.io/badge/Engine-MLX%20%2F%20Local%20SLM-orange.svg?style=flat-square" alt="MLX Engine" /></a>
</p>

---

## 1. Overview

**Selective Delegation Agent (RAT)** is an independently runnable local-first assistant and document intelligence toolkit for macOS. Its desktop shell, CLI, indexing pipeline, retrieval engine, and capability contracts are part of this repository; it does not require another project to function. Local processing is the default for supported workflows. Optional provider-backed features must be configured and invoked explicitly.

The platform operates across two complementary environments:
- **Resident Desktop Shell (RAT)**: A background tray and hotkey-driven interface built on PyQt6 / Qt Quick for instant searching, PDF inspection, and application control.
- **Headless CLI & Kernel**: A modular command-line suite and capability registry for indexing, local Q&A, diagnostics, and code review.

---

## Visual Preview

<p align="center">
  <img src="docs/images/omnibar_search.png" alt="RAT Omnibar Search" width="85%" />
  <br>
  <em>Instant Apple Spotlight-style hybrid search with semantic reranking and latency counters</em>
</p>

<p align="center">
  <img src="docs/images/document_desk.png" alt="RAT Document Desk" width="48%" />
  <img src="docs/images/chat_assistant.png" alt="RAT Assistant Stream" width="48%" />
  <br>
  <em>Left: Document inspection desk with page citations · Right: Local on-device assistant dialogue stream</em>
</p>

---

## 2. What RAT Actually Does

Unlike purely conversational chatbots or theoretical routing benchmarks, RAT integrates directly with your local workspace:

1. **True Hybrid Search (FTS5 + Dense Vectors)**: Indexes local folders and combines SQLite full-text search with vector embeddings via Reciprocal Rank Fusion (RRF) and HyDE query expansion.
2. **Deep Document & PDF Intelligence**: Extracts text, page evidence, and structured excerpts from local PDFs, DOCX, and source trees without uploading them to external servers.
3. **Local SLM Inference**: Executes small language models (such as Qwen 2.5) locally using native MLX on Apple Silicon for zero-cost, offline question answering.
4. **Desktop Automation & System Integration**: Global hotkey activation, macOS Application bundle resolver, and verified system launch workflows.
5. **Headless Code Review & Diagnostics**: Multi-lens diff inspection (missing imports, boundary invariants, code hygiene) and deterministic execution verifiers.

---

## 3. Architecture

```
RAT Runtime Architecture
│
├── rat/os/               Desktop Resident & System Layer
│   ├── app.py            ResidentApplication lifecycle, tray, and event loop
│   ├── crash_shield.py   Global exception protection and crash recovery
│   └── diagnostics.py    Isolated state verification and telemetry
│
├── rat/ui/               Presentation Layer (PyQt6 & Qt Quick)
│   ├── quick_app.py      Quick desktop launcher and application entry
│   ├── quick/            Modular Qt Quick views (Desk, Paper, Mascot, Settings)
│   └── quick_pdf_controller.py  State management and document controller
│
├── rat/engine/           Intelligence & Reasoning Engine
│   ├── hybrid_search.py  FTS5 + vector embedding search via RRF
│   ├── slm.py            Local SLM management and inference
│   ├── mlx_document_session.py  Native Apple Silicon MLX chat runtime
│   └── verification.py   Deterministic operation checkers and verifiers
│
├── rat/crawler/          Filesystem & Storage
│   ├── indexer.py        Document intake, hashing, and chunking
│   └── db.py             SQLite database and FTS5 full-text storage
│
└── rat/kernel/           Modular Capability & Tool Contracts
    ├── registry.py       Capability and OperationDefinition registry
    └── capabilities/     Documents, Applications, Finder, Code Review
```

---

## 4. Privacy & Data Boundaries

* **Local-First Processing**: Document indexing, vector generation, and search queries execute entirely on your machine. No telemetry or personal documents are transmitted to external servers by default.
* **Conditional Escalation**: When optional external models or web lookups are explicitly enabled by the user, only the selected task snippet is sent to the configured provider.
* **Bounded Verifiers**: Operational verifiers run deterministically on local data (AST evaluation, schema validation, evidence matching). They provide reproducible validation for explicitly supported constraints rather than speculative scoring.

---

## 5. Standalone Use & Integration Boundary

RAT is a standalone application, not a wrapper around the other repositories in this GitHub profile. It can be installed and used on its own through the desktop UI or CLI. Its capability registry and MCP server provide optional integration points for external clients.

- **Standalone mode:** run the desktop application or CLI directly from this repository.
- **Agent mode:** use the JSON CLI contract or connect an MCP-compatible client to the stdio server.
- **Extension mode:** external projects may expose their own tools through documented contracts/adapters. They should remain independently installable and should not need to import RAT internals just to provide their core functionality.

RAT does not automatically install, download, or enable every independent project. Each integration has its own dependencies, permissions, and setup.

---

## 6. Getting Started

### Prerequisites
- **macOS** (Optimized for Apple Silicon: M1 / M2 / M3 / M4)
- **Python 3.11+**
- Package manager: [`uv`](https://github.com/astral-sh/uv) (the lock file is the only dependency source)

### Installation

```bash
# Clone repository
git clone https://github.com/Thundercok/selective-delegation-agent.git
cd selective-delegation-agent

# Install the pinned dependencies from uv.lock
uv sync
```

---

## 7. Usage

If using `uv`, you can prefix commands with `uv run` (or activate `.venv` with `source .venv/bin/activate`).

### Launch Desktop Application (GUI)

```bash
# Launch default Unified Qt Quick Desk
uv run python main.py
# (or: python3 main.py with .venv active)

# Launch Quick PDF inspection mode
uv run python main.py quick-pdf
```

### CLI Commands

```bash
# Index configured directories
uv run python main.py index

# Natural language hybrid search
uv run python main.py search "báo cáo tài chính quý 3"

# Query local SLM about an indexed document
uv run python main.py ask "contract_2026.pdf" "What are the payment terms?"

# Offline chat with a specific file using local MLX model
uv run python main.py ask-file /path/to/doc.pdf --model-path /path/to/mlx-model

# Detect duplicate files and document revision trees
uv run python main.py dedup

# Multi-lens automated code review (local diff or GitHub PR)
uv run python main.py review
uv run python main.py review 5 --repo owner/repo

# Check indexing and SLM engine status
uv run python main.py status
```

### Dùng từ agent

People and agents such as Claude Code can call the same CLI. In examples below, `rat` is shorthand for `uv run python main.py` from the repository root; it is not a separately installed executable by default. With `--json`, supported commands print one JSON object to stdout:
`{"schema": "rat.cli/1", "command", "argv", "ok", "exit_code", "data", "view"}`. Agents parse
`data`. `view` is the ViewSpec used for display; logs go to stderr. Nothing asks for input interactively.

Exit codes: `0` ok · `1` failed · `2` invalid command · `3` refused on purpose (the label desk is locked
because the run's `analyze.py` has not run, the named run is not the active one, or a research MLX job is running).

```bash
rat runs status --json            # active run, current step, elapsed time, estimated time left, MLX jobs
rat runs list --json
rat runs pause <run> --json       # SIGSTOP the job tree; <run> is required and must be the active run
rat runs resume <run> --json      # SIGCONT
rat papers add <pdf>... --json    # copy into ~/.rat/papers and index
rat papers ask "<question>" --json  # answer + citations [{n, file, page, snippet}]
rat labels --json                 # which runs are open or locked for labelling
rat labels export <run> --json    # human labels from ~/.rat/labels/<run>.jsonl
rat labels report <run> --json    # Cohen's κ and the confusion matrix
rat tool list --json              # RAT's registered operations
rat tool run <operation> --args '{...}' --json
rat ui <command>                  # open the same command as a view in the desk
rat mcp                           # run RAT's core tools as an MCP stdio server
rat native-sync "<query>"         # sync local hits & stale-revision supersedes links into Native (withnative/native)
```

For MCP clients (Claude Code, Cursor, Native), point stdio transport to:

```json
{
  "command": "uv",
  "args": ["run", "--directory", "/path/to/selective-delegation-agent", "python", "main.py", "mcp"]
}
```

The run monitor only reads `audit/*/run.log` and the process table. The monitored research workflow is intentionally decoupled from RAT: it does not import RAT, so its execution does not depend on the desktop assistant being open. Only explicit `pause`/`resume` commands act on a run. The human-oriented commands (`search`, `ask-file`, and others) remain available; agents should prefer the structured `rat tool run` interface.

---

## 8. Testing & Reliability

The test suite covers unit logic, contract schemas, and isolated diagnostic states. Run from the repository root:

```bash
# Run task memory and capability tests
uv run pytest tests/test_rat_task_memory.py tests/test_code_review_capability.py

# Run verification suite
uv run pytest tests/test_rat_verification.py
```

---

## 9. Current Scope & Known Limitations

- **Platform Specifics**: Resident background integration and hotkeys currently target macOS. Linux and Windows run primarily in headless / CLI mode.
- **Model Hardware Bounds**: MLX inference is available on supported Apple Silicon systems. Performance and feasible model size depend on unified memory; 16GB+ is a practical starting point for smaller quantized models, not a guarantee for every 7B+ workload.
- **Optional Cloud Features**: Any configured external provider has its own data handling terms. Review the provider and the specific command before sending document excerpts or other content.
- **Active Refactoring**: Work is underway to further decouple `rat/main.py` bootstrap routing from the `ResidentApplication` lifecycle.

---

## 10. Roadmap

- [ ] Complete profile configuration to eliminate hardcoded user preferences in CLI.
- [ ] Decouple resident background watcher lifecycle from UI presentation.
- [ ] Export standardized diagnostic health reports with JSON schema validation.
- [ ] Expand standalone cross-platform CLI capabilities.

---

## 11. License

Copyright (C) 2026 Thundercok.

The source code of RAT is released under the [MIT License](LICENSE).

Packaged desktop builds bundle [PyQt6](https://www.riverbankcomputing.com/software/pyqt/), which is licensed under the GPL v3; a distributed `.app` bundle is therefore subject to the GPL v3 as a whole. The offline translation models are OPUS-MT / Argos models under CC-BY-4.0; see `rat/assets/translation/ATTRIBUTION.txt`.
