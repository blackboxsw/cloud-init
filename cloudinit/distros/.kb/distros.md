# Distro Classes

## Distro class role

A distro class abstracts OS-specific behavior for:
- **Package management** — install, remove, upgrade, update sources
- **User management** — add/modify/delete users and groups
- **Hostname** — read and write the system hostname
- **Networking** — select and invoke the appropriate network renderer
- **Locale and timezone** — apply locale settings and set the timezone

The base class is `cloudinit.distros.Distro` in `cloudinit/distros/__init__.py:130`.

## Inheritance model

Most distros are thin subclasses of a family base class:

| Family base | File | `osfamily` value | Covers |
|-------------|------|-----------------|--------|
| `debian.Distro` | `distros/debian.py:38` | `"debian"` | Debian, Ubuntu, Raspberry Pi OS |
| `rhel.Distro` | `distros/rhel.py:21` | `"redhat"` | RHEL, Fedora, CentOS, Amazon, Rocky, Alma, … |
| `bsd.BSD` | `distros/bsd.py:14` | `platform.system().lower()` | FreeBSD, OpenBSD, NetBSD, DragonFly |

A new distro that fits a family only needs to set distro-specific attributes and
override the handful of methods that differ. Copy the smallest existing subclass in
the same family as your starting point.

## Attributes that must be set

| Attribute | Default in base | Notes |
|-----------|----------------|-------|
| `osfamily` | *(no default — annotated `str` at line 156)* | Set in `__init__`; used by `expand_osfamily()` |
| `pip_package_name` | `"python3-pip"` (line 131) | Override if the distro uses a different package name (e.g. Alpine uses `"py3-pip"`) |
| `usr_lib_exec` | `"/usr/lib"` (line 132) | Override for RHEL (`"/usr/libexec"`), FreeBSD (`"/usr/local/lib"`), etc. |

## Methods that must be overridden

Signatures are in `cloudinit/distros/__init__.py`.

| Method | Signature (line) | Purpose |
|--------|-----------------|---------|
| `package_command()` | `(self, command, args=None, pkgs=None)` (line 402) | Install/remove/upgrade packages |
| `update_package_sources()` | `(self, *, force=False)` | Refresh package index (e.g. `apt-get update`) |
| `install_packages()` | `(self, pkglist: PackageList)` | Install a list of packages |
| `_read_hostname()` | `(self, filename, default=None)` (line 490) | Read hostname from file |
| `_write_hostname()` | `(self, hostname, filename)` (line 494) | Write hostname to file |
| `_read_system_hostname()` | `(self)` (line 498) | Read the live system hostname |
| `apply_locale()` | `(self, locale, out_fn=None)` (line 476) | Apply locale settings |
| `set_timezone()` | `(self, tz)` (line 480) | Set the system timezone |

## Methods that delegate to `super()` unless the distro differs

`set_hostname()` (line 391) provides common logic calling `_write_hostname()` and
`_apply_hostname()`; override only if the family base does not handle your distro's
hostname mechanism. Similarly, `apply_locale()` and `set_timezone()` have family
implementations that call shared utilities like `distros.set_etc_timezone()`.

## Network renderer selection

`network_renderer` is a property (line 362) that calls `renderers.select(priority)`
where `priority` comes from `cfg["network"]["renderers"]`. It instantiates the chosen
renderer class and passes renderer-specific config from `self.renderer_configs`. Override
this property only if your distro has a non-standard renderer or requires special config.

## `PackageList` type

Defined at `cloudinit/distros/__init__.py:117`. It is a `Union` accepting:
- `List[str]` — bare package names
- `List[Mapping]` — dicts with package-manager-specific keys
- Mixed lists combining the above

`_extract_package_by_manager()` (line 208) splits a `PackageList` into a
`(packages_by_manager_dict, generic_packages_set)` tuple. Call it in
`install_packages()` to route packages to the correct manager.

## Registration

1. Add the distro class file under `cloudinit/distros/`.
2. Add the distro name(s) to `OSFAMILIES` in `cloudinit/distros/__init__.py:64` under
   the appropriate family key.
3. If the distro does not fit an existing family, add a new family key.

`OSFAMILIES` maps family names to lists of distro name strings. The module loader
(`distros.fetch()`) uses these names to import the correct module at runtime.

## Network refactor note

An ongoing refactor (`WIP-ONGOING-REFACTORIZATION.rst`) is moving networking logic
from `cloudinit.net.*` free functions into the `Distro.networking` instance attribute
(a `Networking` subclass set via `networking_cls`). New distro code should use
`distro.networking.<method>()` rather than calling `cloudinit.net.<function>()`
directly. Check `WIP-ONGOING-REFACTORIZATION.rst` before adding network-related
methods to understand which functions have already been migrated.
