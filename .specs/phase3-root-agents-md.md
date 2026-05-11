# Phase 3: Root `AGENTS.md`

## Goal

Create a root `AGENTS.md` that replaces `CLAUDE.md` as the primary agent
entry point. It must be self-contained enough that an agent starting cold can
orient itself and run the codebase, while staying thin enough that agents load
it without significant context cost.

---

## File to create

### `AGENTS.md` (repository root)

**Target length**: 60–80 lines.

**Do not duplicate** content that lives in `.kb/` directories. Reference it by path.

---

## Required sections

### `## What is cloud-init`

Two to three sentences. State: what it does, when it runs, and the breadth of
platform support. No bullet points — prose only.

### `## Quick-start commands`

A code block table of the most-used `tox` invocations. Must include:

| Command | Purpose |
|---|---|
| `tox -e py3` | Run unit tests |
| `tox -e py3-fast` | Run unit tests in parallel |
| `tox -e py3 -- <path>::<Class>::<method>` | Run a single test |
| `tox -e ruff` | Lint only |
| `tox -e check_format` | Full lint + format check |
| `tox -e do_format` | Auto-format (isort + black + JSON schemas) |
| `tox -e mypy` | Type check |
| `tox -e doc` | Build documentation |

### `## Knowledge base`

A pointer table to the context-local `.kb/` files. One row per knowledge base
file. Format:

```
| Topic | File | Use when… |
```

Rows:
- Architecture → `cloudinit/.kb/architecture.md` → orienting to the boot pipeline or subsystem boundaries
- Core modules → `cloudinit/.kb/core-modules.md` → calling shared helpers (`util`, `subp`, `url_helper`, …)
- Config modules → `cloudinit/config/.kb/cc-modules.md` → creating or modifying a `cc_*.py` module
- Datasources → `cloudinit/sources/.kb/datasources.md` → creating or modifying a `DataSourceXxx.py`
- Distros → `cloudinit/distros/.kb/distros.md` → adding or modifying a distro class
- Testing → `tests/unittests/.kb/testing.md` → writing or debugging unit tests
- Security → `cloudinit/.kb/security.md` → reviewing code that handles user-data or subprocesses
- Conventions → `cloudinit/.kb/conventions.md` → code style, import order, tooling

### `## Subsystem map`

A compact directory-to-purpose table. Must cover:

| Directory | Contents |
|---|---|
| `cloudinit/config/cc_*.py` | Config modules — one feature per file |
| `cloudinit/sources/DataSource*.py` | Cloud platform datasources |
| `cloudinit/distros/` | Per-distro package/user/network management |
| `cloudinit/net/` | Network config parsing and rendering |
| `cloudinit/mergers/` | Config merge strategy implementations |
| `cloudinit/config/schemas/` | JSON schemas for cloud-config validation |
| `tests/unittests/` | Unit tests — layout mirrors `cloudinit/` |
| `tests/integration_tests/` | Integration tests (require cloud or LXD) |

### `## Agent guidance`

Three to five bullet points stating non-obvious rules that apply across all
subsystems:

- `subp.subp()` is blocked in all unit tests by default — see `tests/unittests/.kb/testing.md`
- All new code in `cloudinit/` requires type annotations
- User-data is untrusted input — see `cloudinit/.kb/security.md` before writing code that handles it
- Prefer the shared top-level helpers over the standard library — see `cloudinit/.kb/core-modules.md` (`util.write_file()`/`util.load_text_file()` over `open()`, `subp.subp()` over `subprocess`, `url_helper.readurl()` over `urllib`)
- Subsystem-specific rules are in each directory's own `AGENTS.md`

---

## Migration note

If a root `CLAUDE.md` is present, it holds the same commands and architecture
summary. When creating `AGENTS.md`:
1. Move the commands section verbatim into `## Quick-start commands`
2. Replace the architecture prose with the pointer table (pointing to `.kb/` files)
3. Move testing and code-style content into `tests/unittests/.kb/testing.md` and `cloudinit/.kb/conventions.md` (Phase 1) — do not duplicate here
4. Delete `CLAUDE.md` after `AGENTS.md` is in place, or add a one-line `CLAUDE.md` that points to `AGENTS.md`

If there is no `CLAUDE.md`, skip this note — author `AGENTS.md` directly from
the `.kb/` files.
