# Testing Guide

## Test framework rules

- **pytest only** — no `unittest.TestCase` subclasses.
- Test files mirror source layout under `tests/unittests/`:
  - `cloudinit/config/cc_ntp.py` → `tests/unittests/config/test_cc_ntp.py`
  - `cloudinit/sources/DataSourceEc2.py` → `tests/unittests/sources/test_ec2.py`
  - `cloudinit/util.py` → `tests/unittests/test_util.py`
- Prefer `@pytest.mark.parametrize` over multiple near-identical test functions.

## `subp` blocking

`subp.subp` is **blocked by default** via the `disable_subp_usage` autouse fixture
(`tests/conftest.py:87`). Any unexpected call raises `UnexpectedSubpError`.

| Pattern | When to use |
|---------|-------------|
| `mocker.patch("cloudinit.subp.subp")` | The common case — mock the call and assert on args |
| `@pytest.mark.allow_subp_for("cmd")` | Only when testing real subprocess behavior for that specific command |
| `@pytest.mark.allow_all_subp` | Rarely; integration-level tests only |

## Core fixture catalog

All fixtures below are defined in `tests/unittests/conftest.py` unless noted.

| Fixture | Source | What it provides |
|---------|--------|-----------------|
| `paths` | `conftest.py:235` | `helpers.Paths` backed by a `tmpdir`; use `paths.get_ipath_cur()` for the instance path, `paths.get_cpath()` for the cloud dir |
| `fake_fs` | `conftest.py:154` | pyfakefs-backed filesystem; use instead of mocking `os` or `open` directly |
| `caplog` | pytest built-in | Captured log records; use `caplog.at_level(logging.WARNING)` as a context manager |
| `tmpdir` | pytest built-in | `py.path.local` temporary directory; prefer `paths` fixture for cloud-init paths |
| `Distro` | `conftest.py:31` | Factory function; call `Distro("ubuntu")` to get a real distro instance backed by `paths` |
| `m_gpg` | `conftest.py:40` | `mock.Mock(spec=GPG)` with `list_keys()` and `getkeybyid()` pre-configured; supports context manager use |

## `get_cloud()` helper

`from tests.unittests.util import get_cloud`

Signature: `get_cloud(distro=None, paths=None, sys_cfg=None, metadata=None, mocked_distro=False)`

Returns a `cloud.Cloud` object suitable for passing directly to `handle()`.
- `distro`: distro name string (e.g. `"ubuntu"`); omit for a `MockDistro`.
- `paths`: pass the `paths` fixture to get tmpdir-backed paths.
- `sys_cfg`: extra system config dict.

Source: `tests/unittests/util.py:24`.

## File path assertions

Use `pathlib.Path` rather than string joins:

```python
expected = pathlib.Path(paths.get_ipath_cur()) / "filename.txt"
assert expected.read_text() == "expected content"
```

## Worked example

```python
import logging
import pytest
from tests.unittests.util import get_cloud
from cloudinit.config import cc_final_message

def test_final_message_written(paths, mocker, caplog):
    mocker.patch("cloudinit.subp.subp")
    cloud = get_cloud(paths=paths)
    cfg = {"final_message": "boot done"}
    with caplog.at_level(logging.DEBUG):
        cc_final_message.handle("cloud-final", cfg, cloud, [])
    assert "boot done" in caplog.text
```

This example uses `paths` (tmpdir-backed `Paths`), `mocker.patch` to silence subp,
`get_cloud(paths=paths)` to build a minimal `Cloud`, and `caplog` to assert on log
output — the three most common fixtures used together.
