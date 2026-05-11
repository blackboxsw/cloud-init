# Phase 1: Context Knowledge Base (`.kb/`)

## Goal

Create markdown files in **context-relative `.kb/` subdirectories** directly in
the source tree. Each file lives next to the code it describes, so an agent
working in a subsystem automatically has the knowledge base nearby. The
`AGENTS.md` files (Phases 3–4) reference these files rather than duplicating
their content.

`.kb/` directories are agent-context directories and are not part of the
importable package or test suite.

> One additional knowledge base file — `cloudinit/.kb/core-modules.md`,
> covering the key top-level helper modules — is specified separately in
> **Phase 2**. The architecture file below links to it.

This knowledge base is **prose-and-pointers only**. Do not create code
template files (`*.py` scaffolds) in any `.kb/templates/` directory; agents
copy patterns from the real source tree, guided by the guidelines and
anti-patterns documented here and in Phase 2.

---

## Files to create

### `cloudinit/.kb/architecture.md`

**Purpose**: Orient an agent to the overall system before it touches any code.

**Sections**:
- What cloud-init does (2–3 sentences)
- Four boot stages: name, triggering condition, what runs, key output
- Key subsystems table: subsystem name | directory | base class/entry point | one-line role
- Configuration loading: source priority order (cloud.cfg → cloud.cfg.d → cmdline → metadata → vendor data → user data), pointer to `cloudinit/mergers/`
- Feature flags: `features.py` purpose and downstream patching model
- Shared modules: one-line pointer to `cloudinit/.kb/core-modules.md` for the top-level helper modules (`util`, `subp`, `url_helper`, etc.) that every subsystem depends on

**Constraints**:
- No code snippets — pointers to files and line ranges only
- Must name `cloudinit/cmd/main.py`, `stages.py:Init`, and `mergers/` explicitly

---

### `cloudinit/config/.kb/cc-modules.md`

**Purpose**: Everything needed to correctly create or modify a `cc_*.py` config module.

**Sections**:
- Module contract: three required top-level names (`frequency`, `meta`, `handle`) with their types
- `MetaSchema` fields: `id` (naming convention `cc_<name>`), `distros` (use `ALL_DISTROS` unless distro-specific), `frequency`, `activate_by_schema_keys`
- `activate_by_schema_keys` semantics: module is skipped entirely if none of these keys appear in user-data; use `[]` only if the module must always run
- `frequency` choice guide: `PER_ALWAYS` (every boot), `PER_INSTANCE` (once per instance), `PER_ONCE` (once ever) — with one concrete example each
- `handle(name, cfg, cloud, args)` signature: what each parameter provides, how to read config safely via `util.get_cfg_option_str` / `util.get_cfg_option_list`
- Schema registration: how to add a key to `cloudinit/config/schemas/schema-cloud-config-v1.json` and link it to the module via `activate_by_schema_keys`
- `subp` discipline: always pass a list; never interpolate user-controlled strings into shell commands
- Pointer to shared helpers: `cloudinit/.kb/core-modules.md` for `util.get_cfg_option_*`, `util.write_file`, and `subp.subp`

**Constraints**:
- Include the exact import lines required for a minimal module
- State explicitly that `handle()` must tolerate missing config keys without raising

---

### `cloudinit/sources/.kb/datasources.md`

**Purpose**: Everything needed to correctly implement or modify a `DataSource*.py`.

**Sections**:
- DataSource role: what it exposes (instance ID, hostname, user-data, network config) and when it runs
- Class skeleton: inherit from `sources.DataSource`, set `dsname`, set `local_stage`
- Lifecycle sequence: `_get_data()` → sets `self.metadata`, `self.userdata_raw`, `self.vendordata_raw` → returns bool
- `crawl_metadata()` vs `_get_data()`: crawl fetches raw data from the cloud API, `_get_data` transforms it into the standard attributes
- Network config property: when to override `network_config`, how `EphemeralIPNetwork` is used in local stage sources to fetch metadata before network is configured
- `check_instance_id()`: when to override, what it must return
- `BUILTIN_DS_CONFIG` pattern: how to provide overridable defaults while allowing `sys_cfg` overrides
- URL fetching: always use `url_helper.readurl()` or `url_helper.wait_for_url()`, not `urllib` directly; set reasonable timeouts
- Pointer to shared helpers: `cloudinit/.kb/core-modules.md` for `url_helper` and `util` usage

**Constraints**:
- Must name `cloudinit/sources/__init__.py:DataSource` as the base class
- Explain why `_get_data()` must not raise on "not my platform" — it must return `False`

---

### `cloudinit/distros/.kb/distros.md`

**Purpose**: Guide for adding or modifying a distro class under `cloudinit/distros/`.

**Sections**:
- Distro class role: package management, user management, hostname, networking, locale
- Inheritance: subclass `cloudinit.distros.Distro`; most distros are thin subclasses of a family base (e.g., `debian.py`, `redhat.py`, `bsd.py`)
- Attributes that must be set: `osfamilies`, `pip_package_name`, `usr_lib_exec`
- Methods that must be overridden: `package_command()`, `update_package_sources()`, `install_packages()`; pointer to base class signatures in `cloudinit/distros/__init__.py`
- Methods that delegate to `super()` unless the distro differs: `set_hostname()`, `apply_locale()`, `set_timezone()`
- Network renderer selection: how `network_renderer` property works and when to override it
- `PackageList` type: what it accepts, how `_extract_package_by_manager` splits it
- Registration: where to add the new distro name (`.osfamilies`, `cloudinit/distros/__init__.py:OSFAMILIES`)

**Constraints**:
- Reference actual method signatures from `cloudinit/distros/__init__.py`
- Note the ongoing network refactor (`WIP-ONGOING-REFACTORIZATION.rst`) and what it means for new distro code

---

### `tests/unittests/.kb/testing.md`

**Purpose**: Prevent common test mistakes; provide copy-paste patterns for the most frequent test scenarios.

**Sections**:
- Test framework rules: pytest only (no `unittest.TestCase`); test files mirror source layout under `tests/unittests/`
- `subp` blocking: blocked by default via `disable_subp_usage` autouse fixture; use `mocker.patch("cloudinit.subp.subp")` for the common case; use `@pytest.mark.allow_subp_for("cmd")` only when testing real subprocess behavior
- Core fixture catalog (name | source | what it provides):
  - `paths` → `tests/unittests/conftest.py` → `helpers.Paths` pointing to a tmpdir; use `paths.get_ipath_cur()` for instance path
  - `fake_fs` → `tests/unittests/conftest.py` → pyfakefs-backed filesystem; use instead of mocking `os` directly
  - `caplog` → pytest built-in → captured log output; use `caplog.at_level(logging.WARNING)` context
  - `tmpdir` → pytest built-in → `py.path.local` temp directory
  - `Distro(paths)` → `tests/unittests/conftest.py` → factory; call `Distro("ubuntu")` for a real distro instance
  - `m_gpg` → `tests/unittests/conftest.py` → mocked `GPG` with context manager support
- `get_cloud(paths=paths)` helper from `tests.unittests.util`: creates a minimal `Cloud` object suitable for passing to `handle()`
- `@pytest.mark.parametrize` pattern: prefer over multiple near-identical test methods
- File assertions: use `pathlib.Path(paths.get_ipath_cur()) / "filename"` rather than string joins

**Constraints**:
- All fixture descriptions must match what is actually in `tests/unittests/conftest.py`
- Include one complete worked example (8–15 lines) showing `paths` + `mocker.patch` + `get_cloud` used together

---

### `cloudinit/.kb/security.md`

**Purpose**: Inform security-review agents and code-gen agents about cloud-init's specific threat surface.

**Sections**:
- Execution context: cloud-init runs as root; user-data arrives from the cloud provider and is untrusted
- Threat inventory (each entry: risk name | trigger | mitigation):
  1. **Command injection**: `subp()` called with a list that includes user-controlled strings → always pass a list, never `shell=True` with user data; validate/reject unexpected characters before use
  2. **Path traversal**: `util.write_file()` called with a path derived from user-data → normalize and validate paths; reject `..` components; do not follow symlinks into sensitive directories
  3. **SSRF**: `url_helper.readurl()` called with a user-controlled URL → only fetch URLs from metadata sources; validate scheme and netloc before fetching
  4. **SSTI**: `templater.render_string()` applied to user-provided Jinja templates → already sandboxed in `templater.py`; never bypass the `JinjaSyntaxParsingException` handler
  5. **Privilege retention**: scripts run from user-data execute as root by default → `cc_scripts_*` modules must respect the `default_user` config and drop privileges where specified
- Patterns to flag in review: `shell=True`, `os.system()`, `eval()`, unchecked `chmod`/`chown` targets, bare `urllib` usage outside `url_helper`
- Safe patterns to confirm: `subp(["cmd", arg])` list form, `util.write_file()` with `omode` set, `url_helper.readurl()` with `timeout`

**Constraints**:
- Each threat entry must name the specific cloud-init function or module involved
- No generic OWASP prose — everything must be grounded in this codebase

---

### `cloudinit/.kb/conventions.md`

**Purpose**: Code style and tooling reference; keeps AGENTS.md files from repeating it.

**Sections**:
- Formatting: line length 79 chars (black + ruff); import order via isort `profile = "black"`; shell scripts via `shfmt --case-indent --indent=4 --space-redirects`; JSON schemas via `python3 -m json.tool --indent 2`
- Type annotations: required for all new code in `cloudinit/`; mypy enforced
- Comments: only when the WHY is non-obvious; no docstrings describing what the function name already says
- `subp` over stdlib: always use `cloudinit.subp.subp()` instead of `subprocess` directly
- `util` over stdlib: prefer `util.write_file()`, `util.load_text_file()`, `util.get_cfg_option_*()` over direct `open()`/`os` calls
- tox command reference: table of environment name → purpose → when to run

**Constraints**:
- Keep under 60 lines; this is a quick-reference, not a style guide essay
