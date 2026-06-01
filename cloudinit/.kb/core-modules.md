# Core Modules

These modules are the shared foundation of cloud-init. Agents should prefer
them over the standard library or third-party equivalents. Each entry names the
real file to read for actual signatures and full behaviour.

### cloudinit/util.py
**Purpose**: Catch-all helper — file I/O, decoding, config reads, process and mount helpers.
**Guidelines**:
- Read files with `util.load_text_file()` or `util.load_binary_file()`.
- Write files with `util.write_file(path, content, mode=…)`.
- Read config keys with `util.get_cfg_option_str/list/bool(cfg, key, default)`.
- Parse YAML with `util.load_yaml()`.

**Anti-patterns**:
- Don't call `open()`, `os.remove()`, or `os.makedirs()` directly — use `util.write_file`, `util.del_file`, `util.ensure_dir`.
- Don't index config dicts with `cfg["x"]` — use `get_cfg_option_*` helpers with a default so missing keys never raise.

### cloudinit/subp.py
**Purpose**: The only sanctioned way to run external commands.
**Guidelines**:
- Call `subp.subp(["cmd", arg, …])` with an argument list; catch `subp.ProcessExecutionError`.
- Use `subp.which()` to locate binaries before calling them.

**Anti-patterns**:
- Don't use `subprocess`, `os.system`, or `shell=True`.
- Never build a command by string-concatenating user data — pass a list so arguments are never re-parsed by a shell.

### cloudinit/url_helper.py
**Purpose**: HTTP/FTP fetching for metadata and remote content.
**Guidelines**:
- Use `readurl(url, timeout=…, retries=…)` for single fetches; use `wait_for_url()` when polling a metadata service.
- Always set a `timeout`; handle `UrlError`.

**Anti-patterns**:
- Don't use `urllib`, `requests`, or sockets directly; don't fetch a URL with no timeout (it can hang boot).
- Don't fetch user-controlled URLs outside the metadata flow (see `cloudinit/.kb/security.md`).

### cloudinit/atomic_helper.py
**Purpose**: Crash-safe file writes (write-to-temp-then-rename).
**Guidelines**:
- Use `atomic_helper.write_file()` or `write_json()` for files that must never be observed half-written (state, cache, instance-data).

**Anti-patterns**:
- Don't hand-roll temp-file-and-rename logic.
- Don't use plain `util.write_file` for files another process reads concurrently.

### cloudinit/safeyaml.py
**Purpose**: Safe YAML loading/dumping with schema line-mark tracking.
**Guidelines**:
- Load untrusted YAML through `util.load_yaml()` or `safeyaml.load_with_marks()` when you need line numbers for schema errors.
- Dump with `safeyaml.dumps()`.

**Anti-patterns**:
- Don't call `yaml.load()` or `yaml.full_load()` — they execute arbitrary tags; never use `yaml.Loader` on user-data.

### cloudinit/templater.py
**Purpose**: Sandboxed Jinja/`$var` template rendering for config and files.
**Guidelines**:
- Render via `render_string()`, `render_from_file()`, or `render_to_file()`; let `detect_template()` choose the engine.

**Anti-patterns**:
- Don't construct a raw `jinja2.Environment` or bypass the sandbox.
- Don't swallow `JinjaSyntaxParsingException` — it carries the user's template error and must surface.

### cloudinit/cloud.py
**Purpose**: The `Cloud` facade passed to every config module's `handle()`.
**Guidelines**:
- Read it, don't construct it — use `cloud.datasource`, `cloud.distro`, `cloud.get_hostname()`, `cloud.get_public_ssh_keys()`, and the `get_ipath*`/`get_cpath*` helpers.

**Anti-patterns**:
- Don't instantiate `Cloud` in product code; don't reach around it into datasource internals when a `Cloud` accessor exists.

### cloudinit/helpers.py
**Purpose**: `Paths` (canonical filesystem layout), `Runners`/semaphores (run frequency), and config merging.
**Guidelines**:
- Resolve instance/cloud paths through a `Paths` object (`paths.get_ipath_cur()`, `paths.get_cpath()`, `paths.get_ipath()`).
- Let `Runners` enforce `PER_INSTANCE`/`PER_ONCE` semantics rather than re-checking by hand.

**Anti-patterns**:
- Don't hard-code `/var/lib/cloud/…` paths — derive them from `Paths`; don't reimplement run-once gating.

### cloudinit/settings.py
**Purpose**: Built-in defaults and global constants.
**Guidelines**:
- Import frequency constants (`PER_INSTANCE`, `PER_ALWAYS`, `PER_ONCE`) and `CFG_BUILTIN` from here.

**Anti-patterns**:
- Don't redefine these constants locally or use raw string literals (`"once-per-instance"`, `"always"`, `"once"`).

### cloudinit/features.py
**Purpose**: Compile-time-style feature flags toggling cross-version behaviour.
**Guidelines**:
- Gate behaviour changes behind a module-level boolean and read it as `features.FLAG_NAME`; document the flag where it is defined.

**Anti-patterns**:
- Don't read flags through `get_features()` in hot paths when a direct attribute read works.
- Don't branch on a flag without a comment on what it protects.

### cloudinit/lifecycle.py
**Purpose**: Deprecation logging and version comparison.
**Guidelines**:
- Announce deprecations with `lifecycle.deprecate(…)` or `@deprecate_call(…)`; compare versions via `lifecycle.Version.from_str()`.

**Anti-patterns**:
- Don't log deprecations with a bare `LOG.warning`; don't parse or compare version strings by hand.

### cloudinit/ssh_util.py
**Purpose**: Parsing and updating `authorized_keys` and `sshd_config`.
**Guidelines**:
- Use `parse_authorized_keys()` / `update_authorized_keys()` for key files; use `update_ssh_config()` / `update_ssh_config_lines()` for sshd config.
- Respect strict-mode permission checks (`check_permissions`, `check_create_path`).

**Anti-patterns**:
- Don't edit SSH files with ad-hoc string manipulation; don't relax key-file permissions to work around a strict-mode failure.

### cloudinit/user_data.py
**Purpose**: Parsing the multipart MIME user-data archive.
**Guidelines**:
- Go through `UserDataProcessor` / `convert_string()` for user-data parsing; treat every part as untrusted.

**Anti-patterns**:
- Don't re-parse the MIME structure by hand; don't assume a part has a given content-type without checking.

### cloudinit/stages.py
**Purpose**: Boot orchestration — `Init` (datasource + early stages) and the modules runner.
**Guidelines**:
- Understand the stage order before changing boot flow; route config-loading changes through `fetch_base_config()` / `read_runtime_config()`.

**Anti-patterns**:
- Don't add new boot side effects directly in `Init` — prefer a config module (`cc_*.py`) so behaviour is schema-gated and testable.

---

Out of scope (small or rarely touched by feature work): `version.py`,
`registry.py`, `persistence.py`, `simpletable.py`, `signal_handler.py`,
`socket.py`, `type_utils.py`, `importer.py`.
