---
project: cloud-init
language: python
reviewer_subagent: code-review
model_default: openrouter/moonshotai/kimi-k2.7-code
automation:
  lint: "ruff check ."
  format: "black --check ."
  format_isort: "isort --check-only --diff ."
  typecheck: "mypy cloudinit/"
  tests: "pytest -vv --cov=cloudinit --cov-branch tests/unittests/<path>"
  full_tests: "pytest -vv --cov=cloudinit --cov-branch tests/unittests"
  tox_envs: "ruff, black, isort, mypy, py3"
python_target: "py38"
line_length: 79
formatter: "black + isort (profile black)"
---

# Review Scope

cloud-init is a multi-distro, multi-cloud early-boot service. When reviewing,
keep in mind:

- Code runs as **root** during early boot on many Linux/BSD distros — privilege
  and filesystem operations are sensitive.
- Modules live under `cloudinit/` (config modules in `cloudinit/config/cc_*`,
  datasources in `cloudinit/sources/DataSource*`, distro packers in
  `cloudinit/distros/`, network code in `cloudinit/net/`).
- Tests live under `tests/unittests/` (pytest, mirror the path of the module
  under review, e.g. `cloudinit/util.py` -> `tests/unittests/test_util.py`).
- Cross-distro behavior matters: a change must not break Debian, RHEL, SUSE,
  Alpine, Arch, FreeBSD, NetBSD, or OpenBSD without justification.
- User-facing config changes usually require schema updates
  (`cloudinit/config/schemas/`) and release notes
  (`doc/rtd/changes.rst` / news fragments).

# Guardrails & Code Style

- **Style:** Line length 79, black + isort (profile `black`).
- **Python support:** `target-version = "py38"`. Do not use syntax or stdlib
  features newer than 3.8 (`match` statements, `str.removeprefix`)
- **Type Hinting:** Public function signatures and class attributes should be
  type-hinted. Respect existing `mypy` overrides in `pyproject.toml`.
- **Asynchronous Patterns:** cloud-init is largely synchronous. If async code
  is introduced, never block the event loop with sync I/O — use
  `asyncio.to_thread` for legacy sync libraries.
- **Subprocess / Shell:** Prefer `cloudinit.subp.subp()` / `subp.run_parts()`
  over raw `subprocess`. Reject unquoted shell interpolation in commands run as
  root. Flag `shell=True` with user-controlled input.
- **Memory Management:** Reading cloud metadata, IMDS responses, or user-data
  can be large; prefer streaming / generators (`yield`) over loading entire
  payloads into memory.
- **Logging:** Use module-level `LOG = logging.getLogger(__name__)`. Do not
  log secrets, instance metadata credentials, or user-data payloads. Respect
  `[tool.ruff.lint]` `G` (flake8-logging-format) — use lazy `%`-formatting,
  not f-strings, in log calls.
- **Templating:** Jinja2 templates must be rendered with
  `cloudinit.templater` helpers; never `eval`/`exec` user-supplied templates.

# Security Constraints (Critical)

- **Never Allow Eval:** Immediately reject `eval()`, `exec()`, `compile()` on
  untrusted input, or `pickle.loads()` on untrusted data. User-data and cloud
  metadata are untrusted.
- **Command Injection:** Reject `shell=True` with interpolated strings,
  `os.system()` with user input, and unquoted paths passed to packager tools
  (`apt`, `yum`, `zypper`, `apk`).
- **Path Traversal:** When writing files from metadata/user-data, enforce
  `cloudinit.util` helpers (`write_file`, `ensure_dir`) and validate target
  paths stay within expected roots. Flag `..` or absolute path injection.
- **SQL Injection:** cloud-init rarely uses SQL; if introduced, require
  parameterized queries. Reject f-string/`%` interpolation in SQL.
- **Secrets Handling:** Flag hardcoded API keys, tokens, IMDS credentials, or
  plaintext passwords. Require `os.environ` / `util.get_cfg_path_list` /
  configured sources. Never log credentials or `password:` fields from config.
- **Temp Files:** Use `cloudinit.temp_utils` / `tempfile.NamedTemporaryFile`
  with safe modes; avoid predictable temp paths during early boot.

# Tests & Coverage

- Every behavior change in `cloudinit/` should come with corresponding
  `tests/unittests/` coverage. Identify the correct test module by mirroring
  the source path.
- Prefer `pytest` fixtures and `responses`/`pytest-mock` patterns already used
  in the repo. Avoid network access in unit tests — mock IMDS/metadata
  endpoints.
- Integration tests under `tests/integration_tests/` are not run in review;
  note when a change likely needs a new integration scenario but do not block
  on it.
