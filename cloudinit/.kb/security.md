# Security Model

## Execution context

cloud-init runs as **root**. User-data arrives from the cloud provider and is
**untrusted** — it is opaque bytes that cloud-init decodes and executes on behalf of
the instance owner. Vendor-data is slightly more trusted but still external.

## Threat inventory

### 1. Command injection

**Trigger**: `subp.subp()` called with a command that includes user-controlled strings.

**Mitigation**: Always pass a **list** — never a string with `shell=True`:
```python
# SAFE
subp.subp(["useradd", "--comment", user_provided_comment, username])

# UNSAFE — never do this
subp.subp(f"useradd --comment {user_provided_comment} {username}", shell=True)
```
Validate or reject unexpected characters before passing user strings to system commands.
`subp()` signature is in `cloudinit/subp.py:165`; default is `shell=False`.

### 2. Path traversal

**Trigger**: `util.write_file()` called with a path derived from user-data (e.g. a
user-specified destination for a file in `write_files:`).

**Mitigation**: Normalize the path; reject `..` components; do not follow symlinks
into sensitive directories (`/etc`, `/root`, etc.). `write_file()` does not itself
validate paths — callers must sanitize. Function at `cloudinit/util.py:2243`.

### 3. SSRF

**Trigger**: `url_helper.readurl()` called with a URL that comes from user-data or
a user-controlled config key.

**Mitigation**: Only fetch URLs from trusted metadata sources (IMDS endpoints defined
in `BUILTIN_DS_CONFIG`). Validate scheme (`https://` or the cloud-specific HTTP
metadata endpoint) and netloc before fetching. Never pass arbitrary user-provided URLs
to `readurl()`. Function at `cloudinit/url_helper.py:451`.

### 4. SSTI (Server-Side Template Injection)

**Trigger**: `templater.render_string()` applied to user-provided Jinja templates
(`#cloud-config` with `## template: jinja` header).

**Mitigation**: Already sandboxed via `UndefinedJinjaVariable` (`templater.py:74`)
which returns a safe placeholder for undefined variables instead of raising. Never
bypass the `JinjaSyntaxParsingException` handler (`templater.py:31`). Allowed
extensions are restricted to `["jinja2.ext.do"]` only (`templater.py:142`).

### 5. Privilege retention

**Trigger**: Scripts from user-data (`cc_scripts_user`, `cc_scripts_per_instance`,
`cc_scripts_per_boot`, `cc_scripts_per_once`) execute as the cloud-init process user
(root) by default.

**Mitigation**: `cc_scripts_*` modules call `subp.runparts()` (`subp.py:350`). The
optional `exe_prefix` parameter (used in `cc_scripts_vendor`) allows a privilege
prefix (e.g. `sudo -u nobody`). Modules that need to drop privileges must construct
an appropriate prefix and pass it explicitly; there is no automatic privilege dropping.

## Patterns to flag in review

- `shell=True` anywhere in `subp.subp()` calls
- `os.system()` or `subprocess.run(..., shell=True)` — use `subp.subp()` instead
- `eval()` on any external data
- `chmod` / `chown` targets derived from user-data without path validation
- `urllib` used directly outside of `cloudinit/url_helper.py`
- Unvalidated paths passed to `util.write_file()` or `open()`

## Safe patterns to confirm

- `subp.subp(["cmd", arg])` — list form with no shell interpolation
- `util.write_file(path, content, omode="wb")` — with explicit open mode
- `url_helper.readurl(url, timeout=10)` — with explicit timeout and trusted URL
- `url_helper.wait_for_url(urls, max_wait=120, timeout=10)` — with both wait and per-request timeout set
