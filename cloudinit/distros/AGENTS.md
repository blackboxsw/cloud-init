## cloudinit/distros — distro classes

Distro classes implement package management, user management, and network
configuration for a specific Linux/BSD family.

Full contract: cloudinit/distros/.kb/distros.md

### Rules

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

### Test location

`tests/unittests/distros/test_<distroname>.py`
