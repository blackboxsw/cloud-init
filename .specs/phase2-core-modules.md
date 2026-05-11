# Phase 2: Key Top-Level Module Guidelines (`cloudinit/.kb/core-modules.md`)

## Goal

Create a single knowledge base file, `cloudinit/.kb/core-modules.md`, that
documents the **key top-level Python modules** in `cloudinit/` — the shared
helpers every subsystem imports. For each module the file gives an agent three
things and nothing more:

- **Purpose** — one line on what the module is for.
- **Guidelines** — the handful of expectations an agent must meet when calling
  into or extending it.
- **Anti-patterns** — the specific mistakes to avoid, phrased as "don't X; do Y".

This file replaces the code-template approach. **Do not create any `*.py`
template scaffolds.** Agents learn the correct shape by reading the real source
(every guideline below names the module to read) plus these guidelines.

`cloudinit/.kb/` is an agent-context directory — not importable, not tested.

---

## File to create

### `cloudinit/.kb/core-modules.md`

**Target length**: 90–140 lines. Prose-and-pointers only; no code blocks
longer than a single call signature.

**Opening**: One short paragraph stating that these modules are the shared
foundation, that agents should prefer them over the standard library, and that
each entry names the file to read for the real signatures.

**Format per module**: a `### cloudinit/<module>.py` heading, then a one-line
**Purpose**, a short **Guidelines** list, and a short **Anti-patterns** list.
Keep each module entry to ~6–10 lines.

---

## Modules to cover (in this order)

### `cloudinit/util.py`
- Purpose: the catch-all helper module — file I/O, decoding, config reads,
  process/mount helpers.
- Guidelines: read/write files with `util.load_text_file()`,
  `util.load_binary_file()`, `util.write_file(path, content, mode=…)`; read
  config with `util.get_cfg_option_str/list/bool(cfg, key, default)`; parse YAML
  with `util.load_yaml()`.
- Anti-patterns: don't call `open()`, `os.remove()`, or `os.makedirs()`
  directly — use `util.write_file`, `util.del_file`, `util.ensure_dir`; don't
  index config dicts (`cfg["x"]`) — use the `get_cfg_option_*` helpers with a
  default so missing keys never raise.

### `cloudinit/subp.py`
- Purpose: the only sanctioned way to run external commands.
- Guidelines: call `subp.subp(["cmd", arg, …])` with an argument list; catch
  `subp.ProcessExecutionError`; use `subp.which()` to locate binaries.
- Anti-patterns: don't use `subprocess`, `os.system`, or `shell=True`; never
  build a command by string-concatenating user-data — pass a list so arguments
  are never re-parsed by a shell.

### `cloudinit/url_helper.py`
- Purpose: HTTP/FTP fetching for metadata and remote content.
- Guidelines: use `readurl(url, timeout=…, retries=…)` for single fetches and
  `wait_for_url()` when polling a metadata service; always set a `timeout`;
  handle `UrlError`.
- Anti-patterns: don't use `urllib`, `requests`, or sockets directly; don't
  fetch a URL with no timeout (it can hang boot); don't fetch user-controlled
  URLs outside the metadata flow (see `cloudinit/.kb/security.md`).

### `cloudinit/atomic_helper.py`
- Purpose: crash-safe file writes (write-to-temp-then-rename).
- Guidelines: use `atomic_helper.write_file()` / `write_json()` for files that
  must never be observed half-written (state, cache, instance-data).
- Anti-patterns: don't hand-roll temp-file-and-rename logic; don't use plain
  `util.write_file` for files another process reads concurrently.

### `cloudinit/safeyaml.py`
- Purpose: safe YAML loading/dumping with schema line-mark tracking.
- Guidelines: load untrusted YAML through `util.load_yaml()` (which wraps the
  safe loader) or `safeyaml.load_with_marks()` when you need line numbers for
  schema errors; dump with `safeyaml.dumps()`.
- Anti-patterns: don't call `yaml.load()` / `yaml.full_load()` — they execute
  arbitrary tags; never use `yaml.Loader` on user-data.

### `cloudinit/templater.py`
- Purpose: sandboxed Jinja/`$var` template rendering for config and files.
- Guidelines: render via `render_string()`, `render_from_file()`, or
  `render_to_file()`; let `detect_template()` choose the engine.
- Anti-patterns: don't construct a raw `jinja2.Environment` or bypass the
  sandbox; don't swallow `JinjaSyntaxParsingException` — it carries the user's
  template error and must surface.

### `cloudinit/cloud.py`
- Purpose: the `Cloud` facade passed to every config module's `handle()`.
- Guidelines: read it, don't construct it — use `cloud.datasource`,
  `cloud.distro`, `cloud.get_hostname()`, `cloud.get_public_ssh_keys()`, and
  the `get_ipath*/get_cpath*` path helpers.
- Anti-patterns: don't instantiate `Cloud` in product code; don't reach around
  it into the datasource internals when a `Cloud` accessor exists.

### `cloudinit/helpers.py`
- Purpose: `Paths` (canonical filesystem layout), `Runners`/semaphores (run
  frequency), and config merging.
- Guidelines: resolve instance/cloud paths through a `Paths` object
  (`paths.get_ipath_cur()`, `paths.get_cpath()`); let `Runners` enforce
  `PER_INSTANCE`/`PER_ONCE` semantics rather than re-checking by hand.
- Anti-patterns: don't hard-code `/var/lib/cloud/...` paths — derive them from
  `Paths`; don't reimplement run-once gating.

### `cloudinit/settings.py`
- Purpose: built-in defaults and global constants.
- Guidelines: import frequency constants (`PER_INSTANCE`, `PER_ALWAYS`,
  `PER_ONCE`) and `CFG_BUILTIN` from here.
- Anti-patterns: don't redefine these constants locally or use the raw string
  literals (`"once-per-instance"`).

### `cloudinit/features.py`
- Purpose: compile-time-style feature flags toggling cross-version behavior.
- Guidelines: gate behavior changes behind a module-level boolean here and read
  it as `features.FLAG_NAME`; document the flag where it is defined.
- Anti-patterns: don't read flags through `get_features()` in hot paths when a
  direct attribute read works; don't branch on a flag without a comment on what
  it protects.

### `cloudinit/lifecycle.py`
- Purpose: deprecation logging and version comparison.
- Guidelines: announce deprecations with `lifecycle.deprecate(...)` /
  `@deprecate_call(...)`; compare versions via `lifecycle.Version.from_str()`.
- Anti-patterns: don't log deprecations with a bare `LOG.warning`; don't parse
  or compare version strings by hand.

### `cloudinit/ssh_util.py`
- Purpose: parsing and updating `authorized_keys` and `sshd_config`.
- Guidelines: use `parse_authorized_keys()` / `update_authorized_keys()` and
  `update_ssh_config()` / `update_ssh_config_lines()`; respect strict-mode
  permission checks (`check_permissions`, `check_create_path`).
- Anti-patterns: don't edit SSH files with ad-hoc string manipulation; don't
  relax key-file permissions to work around a strict-mode failure.

### `cloudinit/user_data.py`
- Purpose: parsing the multipart MIME user-data archive.
- Guidelines: go through `UserDataProcessor` / `convert_string()` for user-data
  parsing; treat every part as untrusted.
- Anti-patterns: don't re-parse the MIME structure by hand; don't assume a part
  has a given content-type without checking.

### `cloudinit/stages.py`
- Purpose: boot orchestration — `Init` (datasource + early stages) and the
  modules runner.
- Guidelines: understand the stage order before changing boot flow; route
  config-loading changes through `fetch_base_config()` /
  `read_runtime_config()`.
- Anti-patterns: don't add new boot side effects directly in `Init`; prefer a
  config module (`cc_*.py`) so behavior is schema-gated and testable.

---

## Constraints

- Every module entry must name the real file so an agent can read the actual
  signatures; the KB file itself contains **no copyable code template**.
- Guidelines and anti-patterns must be grounded in this codebase — name real
  functions/classes (verified against the source), not generic advice.
- Keep it scannable: short bullets, imperative voice ("use X", "don't call Y").
- Out of scope (mention in one closing line, do not document individually):
  `version.py`, `registry.py`, `persistence.py`, `simpletable.py`,
  `signal_handler.py`, `socket.py`, `type_utils.py`, `importer.py` — small or
  rarely touched by feature work.
