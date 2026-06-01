# cloud-init — Agent Entry Point

## What is cloud-init

cloud-init is the industry-standard tool for initialising cloud instances on first
boot: it applies user-data, sets hostnames, configures networking, creates users,
and runs arbitrary scripts before the system is handed to the user. It runs once,
early in the boot sequence, across more than 100 cloud platforms including AWS,
Azure, GCP, and OpenStack as well as bare-metal provisioning tools.

---

## Quick-start commands

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

---

## Knowledge base

| Topic | File | Use when… |
|---|---|---|
| Architecture | `cloudinit/.kb/architecture.md` | orienting to the boot pipeline or subsystem boundaries |
| Core modules | `cloudinit/.kb/core-modules.md` | calling shared helpers (`util`, `subp`, `url_helper`, …) |
| Config modules | `cloudinit/config/.kb/cc-modules.md` | creating or modifying a `cc_*.py` module |
| Datasources | `cloudinit/sources/.kb/datasources.md` | creating or modifying a `DataSourceXxx.py` |
| Distros | `cloudinit/distros/.kb/distros.md` | adding or modifying a distro class |
| Testing | `tests/unittests/.kb/testing.md` | writing or debugging unit tests |
| Security | `cloudinit/.kb/security.md` | reviewing code that handles user-data or subprocesses |
| Conventions | `cloudinit/.kb/conventions.md` | code style, import order, tooling |

---

## Subsystem map

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

---

## Agent guidance

- `subp.subp()` is blocked in all unit tests by default — see `tests/unittests/.kb/testing.md`
- All new code in `cloudinit/` requires type annotations
- User-data is untrusted input — see `cloudinit/.kb/security.md` before writing code that handles it
- Prefer the shared top-level helpers over the standard library — see `cloudinit/.kb/core-modules.md` (`util.write_file()`/`util.load_text_file()` over `open()`, `subp.subp()` over `subprocess`, `url_helper.readurl()` over `urllib`)
- Subsystem-specific rules are in each directory's own `AGENTS.md`
