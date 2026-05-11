# Phase 4: Subsystem `AGENTS.md` Files

## Goal

Create four `AGENTS.md` files, one per key subsystem directory. Each file is
scoped to the code in that directory: it gives an agent landing in that
directory everything it needs without forcing it to read the entire knowledge
base upfront. The `.kb/` directory in the same subtree holds the full
reference detail.

**Target length per file**: 25–40 lines.

---

## Files to create

### `cloudinit/config/AGENTS.md`

**Audience**: An agent creating or modifying a `cc_*.py` config module.

**Required content**:

1. One-sentence role statement: config modules implement individual cloud-config
   features; each module corresponds to one or more user-data keys.

2. Reference line: `Full contract: cloudinit/config/.kb/cc-modules.md`

3. Reference line: `Shared helpers: cloudinit/.kb/core-modules.md`

4. **Rules** (state these explicitly — they are the most commonly violated):
   - `activate_by_schema_keys` must exactly match the key names declared in
     `cloudinit/config/schemas/schema-cloud-config-v1.json`; a mismatch causes
     the module to never run when those keys are present
   - `handle()` must not raise when the relevant config keys are absent from
     `cfg` — use `util.get_cfg_option_*()` with a default, not direct dict access
   - `subp()` arguments must be a list; never pass user-controlled strings
     directly to shell execution
   - New config keys require a corresponding JSON schema entry — add to
     `schema-cloud-config-v1.json` and reference from `activate_by_schema_keys`

5. **Test location**: `tests/unittests/config/test_cc_<name>.py`

---

### `cloudinit/sources/AGENTS.md`

**Audience**: An agent creating or modifying a `DataSource*.py`.

**Required content**:

1. One-sentence role statement: datasources abstract cloud-platform metadata
   into a uniform interface; cloud-init selects one datasource per boot.

2. Reference line: `Full contract: cloudinit/sources/.kb/datasources.md`

3. Reference line: `Shared helpers: cloudinit/.kb/core-modules.md`

4. **Rules**:
   - `_get_data()` must return `False` (not raise) when the datasource detects
     it is not running on its target platform; raising causes cloud-init to abort
   - `_get_data()` must set `self.metadata` before returning `True`; downstream
     code assumes it is always populated after a successful call
   - Do not make network calls in `__init__` or at import time; all I/O belongs
     in `_get_data()` or `crawl_metadata()`
   - Local-stage datasources (`local_stage = True`) must handle the case where
     no network interface is available yet; use `EphemeralIPNetwork` for any
     required metadata fetch

5. **Test location**: `tests/unittests/sources/test_<dsname>.py`

---

### `cloudinit/distros/AGENTS.md`

**Audience**: An agent adding a new distro or modifying distro-specific behavior.

**Required content**:

1. One-sentence role statement: distro classes implement package management,
   user management, and network configuration for a specific Linux/BSD family.

2. Reference line: `Full contract: cloudinit/distros/.kb/distros.md`

3. **Rules**:
   - Most new distros subclass an existing family base (`debian.py`,
     `redhat.py`, `bsd.py`) rather than `Distro` directly; check the family
     first before overriding methods
   - `package_command()` and `update_package_sources()` must be overridden if
     the distro uses a package manager not already covered by the family base
   - Network rendering is selected via the `network_renderer` property; override
     it only if the distro requires a renderer not used by its family
   - The ongoing network refactor (`WIP-ONGOING-REFACTORIZATION.rst`) is moving
     network logic into per-distro `Networking` classes; new network code should
     follow that pattern, not extend the old `Distro` network methods directly
   - Register the new distro name in `cloudinit/distros/__init__.py:OSFAMILIES`

4. **Test location**: `tests/unittests/distros/test_<distroname>.py`

---

### `tests/unittests/AGENTS.md`

**Audience**: An agent writing or modifying unit tests.

**Required content**:

1. One-sentence role statement: unit tests live under `tests/unittests/` and
   mirror the `cloudinit/` directory structure.

2. Reference line: `Full reference: tests/unittests/.kb/testing.md`

3. **Rules**:
   - Never use `unittest.TestCase`; use plain pytest classes or functions
   - `subp.subp` is blocked by the `disable_subp_usage` autouse fixture;
     mock it with `mocker.patch("cloudinit.subp.subp")` for the common case;
     only use `@pytest.mark.allow_subp_for` when the test is explicitly
     verifying subprocess behavior
   - Never mock `os`, `os.path`, or `open` directly — use the `fake_fs`
     fixture, which wraps pyfakefs and handles `util.*` file functions correctly
   - Use `paths` (not `tmpdir`) for anything that goes through `cloud.paths` or
     `util.*` path helpers; `tmpdir` is for truly isolated scratch files
   - `get_cloud(paths=paths)` from `tests.unittests.util` produces the minimal
     `Cloud` object needed for `handle()` calls; do not construct `Cloud` manually
   - Prefer `@pytest.mark.parametrize` over multiple near-identical test methods
