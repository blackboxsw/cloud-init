## cloudinit/sources — datasources

Datasources abstract cloud-platform metadata into a uniform interface;
cloud-init selects one datasource per boot.

Full contract: cloudinit/sources/.kb/datasources.md
Shared helpers: cloudinit/.kb/core-modules.md

### Rules

- `_get_data()` must return `False` (not raise) when the datasource detects
  it is not running on its target platform; raising causes cloud-init to abort
- `_get_data()` must set `self.metadata` before returning `True`; downstream
  code assumes it is always populated after a successful call
- Do not make network calls in `__init__` or at import time; all I/O belongs
  in `_get_data()` or `crawl_metadata()`
- Local-stage datasources (`local_stage = True`) must handle the case where
  no network interface is available yet; use `EphemeralIPNetwork` for any
  required metadata fetch

### Test location

`tests/unittests/sources/test_<dsname>.py`
