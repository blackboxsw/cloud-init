# cloud-init Architecture

## What cloud-init does

cloud-init is the industry-standard, multi-distribution method for cross-platform
cloud instance initialization. It identifies the cloud environment during early boot,
reads cloud metadata (and optional user/vendor data) from the datasource, and
initializes the system accordingly — configuring networking, SSH access, package
installation, and arbitrary provisioning tasks.

## Boot stages

| Stage | Trigger | Entry point | What runs | Key output |
|-------|---------|-------------|-----------|------------|
| **init-local** | Early boot, no network | `main_init(--local)` in `cloudinit/cmd/main.py:447` | Local datasource detection; filesystem-based seeds; minimal config | `self.datasource` set; per-boot scripts skipped |
| **init** (network) | After network up | `main_init()` in `cloudinit/cmd/main.py:447` | Remote datasource fetch; metadata, user-data, vendor-data consumed; handlers run | Instance ID written; config consumed |
| **modules-config** | After init stage | `main_modules(mode="config")` in `cloudinit/cmd/main.py:745` | `cloud_config_modules` list: packages, users, hostname, locale, etc. | System configured |
| **modules-final** | After config stage | `main_modules(mode="final")` in `cloudinit/cmd/main.py:745` | `cloud_final_modules` list: scripts, phone-home, final-message | `boot-finished` written |

Stage orchestration lives in `cloudinit/stages.py`; the `Init` class (`stages.py:140`)
drives datasource discovery and module execution.

## Key subsystems

| Subsystem | Directory | Base class / entry point | Role |
|-----------|-----------|--------------------------|------|
| Config modules | `cloudinit/config/` | `cc_*.py:handle()` | User-facing cloud-config features |
| Datasources | `cloudinit/sources/` | `sources/__init__.py:DataSource` | Cloud platform detection and metadata fetch |
| Handlers | `cloudinit/handlers/` | `handlers/__init__.py:ContentHandler` | Decode user-data parts (scripts, cloud-config, jinja) |
| Distros | `cloudinit/distros/` | `distros/__init__.py:Distro` | OS-specific package, user, hostname, network ops |
| Networking | `cloudinit/net/` | `net/__init__.py` | Network config generation and rendering |
| CLI | `cloudinit/cmd/` | `cmd/main.py:main()` | Entry points for each boot stage |
| Mergers | `cloudinit/mergers/` | `mergers/__init__.py:LookupMerger` | Pluggable config merge strategies |
| Reporting | `cloudinit/reporting/` | `reporting/__init__.py` | Event reporting and status tracking |

## Configuration loading

Sources are merged in priority order (highest wins):

1. **Kernel cmdline** — `util.read_conf_from_cmdline()` (`helpers.py:1156`)
2. **Runtime config** — `/run/cloud-init/cloud.cfg` (`helpers.py:1154`)
3. **System config** — `/etc/cloud/cloud.cfg` + `/etc/cloud/cloud.cfg.d/*.cfg` (`helpers.py:1150`)
4. **Built-in defaults** — `cloudinit/settings.py` via `util.get_builtin_cfg()` (`helpers.py:1148`)

After the base config is built, `ConfigMerger` (`cloudinit/helpers.py:162`) layers on top:

5. **User-data** cloud-config (from datasource)
6. **Vendor-data** (static, then dynamic)
7. **Datasource** config object

Merge strategies for nested dicts/lists come from `cloudinit/mergers/`. The default
strategy (`"list()+dict()+str()"`) is defined in `mergers/__init__.py:11`.

## Feature flags

`cloudinit/features.py` holds module-level boolean (or string) constants that act as
build-time toggles. Downstream distributions patch this file directly via quilt patches
to alter behavior without full forks. `get_features()` (`features.py:146`) returns a
dict of all current values. Tests must verify all valid flag states.

Examples: `ERROR_ON_USER_DATA_FAILURE` (line 21), `NETPLAN_CONFIG_ROOT_READ_ONLY` (line 62).

## Shared helpers

The top-level helper modules that every subsystem depends on are documented in
`cloudinit/.kb/core-modules.md`. Key modules: `util`, `subp`, `url_helper`, `helpers`,
`ssh_util`, `cloud`, `stages`, `atomic_helper`.
