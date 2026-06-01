# Config Modules (`cc_*.py`)

## Module contract

Every `cc_*.py` must define exactly three module-level names:

| Name | Type | Purpose |
|------|------|---------|
| `frequency` | `str` | One of the `PER_*` constants; also stored in `meta` |
| `meta` | `MetaSchema` | Module metadata dict (see below) |
| `handle` | `function` | Entry point called by the stage runner |

Minimal imports for a new module:

```python
import logging
from cloudinit.cloud import Cloud
from cloudinit.config import Config
from cloudinit.config.schema import MetaSchema
from cloudinit.settings import PER_INSTANCE  # or PER_ALWAYS / PER_ONCE
```

`MetaSchema` is a `TypedDict` defined in `cloudinit/config/schema.py:84`.

## `MetaSchema` fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Module identifier, naming convention `cc_<name>` (e.g. `"cc_write_files"`) |
| `distros` | `List[str]` | Use `["all"]` (or import `ALL_DISTROS` from `cloudinit.distros`) unless the module is distro-specific |
| `frequency` | `str` | One of the three constants below |
| `activate_by_schema_keys` | `List[str]` | Optional; see semantics below |

## `activate_by_schema_keys` semantics

Defined in `cloudinit/config/schema.py:84` and evaluated in
`cloudinit/config/modules.py:93`.

- **Empty list `[]`**: module always runs (when frequency and distro match).
- **Non-empty list**: module is skipped entirely if **none** of the listed keys appear
  in the user-data dict. Use `[]` only for modules that must run unconditionally (e.g.
  `cc_final_message`).

Examples:
- `cc_write_files` uses `["write_files"]` — skipped unless the user provides `write_files:`.
- `cc_ntp` uses `["ntp"]` — skipped unless `ntp:` is present.
- `cc_ca_certs` uses `["ca_certs", "ca-certs"]` — either key triggers the module.

## Frequency choice guide

Constants are defined in `cloudinit/settings.py:74`.

| Constant | Value | When to use | Example module |
|----------|-------|-------------|----------------|
| `PER_ALWAYS` | `"always"` | Must run on every boot regardless of state | `cc_final_message` (`cc_final_message.py:20`), `cc_growpart` |
| `PER_INSTANCE` | `"once-per-instance"` | Idempotent setup that should repeat on new instances | `cc_write_files` (`cc_write_files.py:29`), `cc_ntp` |
| `PER_ONCE` | `"once"` | One-time provisioning that must never repeat | `cc_scripts_per_once` (`cc_scripts_per_once.py:23`) |

## `handle(name, cfg, cloud, args)` signature

Defined at the module level; type signature:
`def handle(name: str, cfg: Config, cloud: Cloud, args: list) -> None`

| Parameter | Provides |
|-----------|----------|
| `name` | Module name string (e.g. `"cloud-final"`) |
| `cfg` | Full cloud-config dict from user data (`Config` is an alias for `dict`) |
| `cloud` | Runtime context: `cloud.datasource`, `cloud.distro`, `cloud.paths`, `cloud.get_hostname()` |
| `args` | CLI arguments when module is invoked via `cloud-init single`; usually `[]` |

**`handle()` must tolerate missing config keys without raising.** Use
`util.get_cfg_option_str(cfg, "key", default)` and
`util.get_cfg_option_list(cfg, "key", default)` (both in `cloudinit/util.py:491`)
rather than direct dict access.

## Schema registration

1. Add the top-level key and its JSON schema to
   `cloudinit/config/schemas/schema-cloud-config-v1.json`.
2. List that same key in `activate_by_schema_keys` in the module's `meta`.

This links validation to activation: the schema validates the key's shape; the
`activate_by_schema_keys` list ensures the module only runs when the key is present.

## `subp` discipline

- Always pass a **list**: `subp.subp(["cmd", arg1, arg2])`.
- Never pass `shell=True` with any user-controlled string.
- Never interpolate user-provided values into a shell command string.
- Import: `from cloudinit import subp`, then call `subp.subp([...])`.

See `cloudinit/.kb/security.md` for the full threat model.

## Shared helpers pointer

`cloudinit/.kb/core-modules.md` documents `util.get_cfg_option_*`,
`util.write_file`, and `subp.subp` in detail.
