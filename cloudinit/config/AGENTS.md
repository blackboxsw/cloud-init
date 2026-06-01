## cloudinit/config — config modules

Config modules implement individual cloud-config features; each module
corresponds to one or more user-data keys.

Full contract: cloudinit/config/.kb/cc-modules.md
Shared helpers: cloudinit/.kb/core-modules.md

### Rules

- `activate_by_schema_keys` must exactly match the key names declared in
  `cloudinit/config/schemas/schema-cloud-config-v1.json`; a mismatch causes
  the module to never run when those keys are present
- `handle()` must not raise when the relevant config keys are absent from
  `cfg` — use `util.get_cfg_option_*()` with a default, not direct dict access
- `subp()` arguments must be a list; never pass user-controlled strings
  directly to shell execution
- New config keys require a corresponding JSON schema entry — add to
  `schema-cloud-config-v1.json` and reference from `activate_by_schema_keys`

### Test location

`tests/unittests/config/test_cc_<name>.py`
