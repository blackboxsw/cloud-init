# DataSources

## DataSource role

A datasource identifies the cloud platform, then exposes the instance's:

- **Instance ID** — `get_instance_id()` (`sources/__init__.py:837`)
- **Hostname** — `get_hostname()` returns a `DataSourceHostname` NamedTuple
- **User-data** — `userdata_raw` attribute; decoded by handlers
- **Vendor-data** — `vendordata_raw` / `vendordata2_raw`
- **Network config** — `network_config` property (returns `None` unless overridden)
- **Metadata dict** — `self.metadata` with at minimum `"instance-id"` and `"local-hostname"`

Datasources run in either the **init-local** stage (before network) or the **init**
(network) stage depending on their `dsmode`. The stage runner calls `ds.get_data()`
which invokes `_check_and_get_data()` (`sources/__init__.py:427`).

## Class skeleton

```python
from cloudinit import sources

class DataSourceMyCloud(sources.DataSource):
    dsname = "MyCloud"          # must be unique; used in config key "datasource.MyCloud"
    # For local-stage sources only:
    # dsmode = sources.DSMODE_LOCAL
```

Inherit from `cloudinit.sources.__init__.DataSource` (`sources/__init__.py:199`).
The `dsname` attribute (line 206) must be set; it is used as the config key and log label.

## Lifecycle: `_get_data()`

`_get_data()` is the one abstract method every datasource must implement
(`sources/__init__.py:603`). It:

1. Optionally sets up an ephemeral network (local-stage only — see below).
2. Calls `crawl_metadata()` to fetch raw data from the cloud API.
3. Populates `self.metadata`, `self.userdata_raw`, `self.vendordata_raw`.
4. Stores the raw crawl result in `self._crawled_metadata` for persistence.
5. **Returns `True` on success, `False` if this is not the right platform.**

`_get_data()` must **never raise** on "not my platform" — return `False` so the
stage runner can try the next datasource in the priority list.

## `crawl_metadata()` vs `_get_data()`

| Method | Responsibility | Return type |
|--------|---------------|-------------|
| `crawl_metadata()` | Fetch raw bytes/dicts from the cloud IMDS endpoint | `dict` with keys `"meta-data"`, `"user-data"`, `"vendor-data"` |
| `_get_data()` | Orchestrate (network setup + crawl + parse + persist) | `bool` |

`crawl_metadata()` may be called multiple times (e.g. retry logic); `_get_data()`
is called once per boot. See `DataSourceEc2.crawl_metadata()` (`DataSourceEc2.py:561`)
for a canonical example.

## `network_config` property

The base class returns `None` (`sources/__init__.py:1005`). Override it when the
datasource provides network topology metadata. Cache the result:

```python
@property
def network_config(self):
    if self._network_config != sources.UNSET:
        return self._network_config
    self._network_config = self._build_network_config()
    return self._network_config
```

Initialize `self._network_config = sources.UNSET` in `__init__`.

## `EphemeralIPNetwork` for local-stage sources

Local-stage datasources have no network. `EphemeralIPNetwork`
(`cloudinit/net/ephemeral.py:394`) is a context manager that brings up a temporary
DHCP or link-local interface, runs the body (metadata fetch), then tears down:

```python
from cloudinit.net.ephemeral import EphemeralIPNetwork

with EphemeralIPNetwork(self.distro, candidate_nic, ipv4=True) as netw:
    self._crawled_metadata = self.crawl_metadata()
```

Set `perform_dhcp_setup = True` on the local-stage subclass to signal that DHCP is
needed before any metadata fetch (see `DataSourceEc2Local`, `DataSourceEc2.py:721`).

## `check_instance_id()`

Override to provide a fast local check (no network) of whether the cached instance
ID is still valid. Returns `bool`. The common implementation:

```python
def check_instance_id(self, sys_cfg) -> bool:
    return sources.instance_id_matches_system_uuid(self.get_instance_id())
```

`instance_id_matches_system_uuid()` is defined at `sources/__init__.py:1141` and
compares against DMI data. Return `False` from the base class default if not overriding.

## `BUILTIN_DS_CONFIG` pattern

Provide overridable defaults without hard-coding URLs or timeouts:

```python
BUILTIN_DS_CONFIG = {
    "metadata_url": "http://169.254.169.254/",
    "max_wait": 120,
}

class DataSourceMyCloud(sources.DataSource):
    def __init__(self, sys_cfg, distro, paths):
        super().__init__(sys_cfg, distro, paths)
        self.ds_cfg = util.mergemanydict([
            util.get_cfg_by_path(sys_cfg, ["datasource", self.dsname], {}),
            BUILTIN_DS_CONFIG,
        ])
```

User config takes precedence; `BUILTIN_DS_CONFIG` supplies safe defaults.
See `DataSourceGCE.py:20` and `DataSourceHetzner.py:19` for examples.

## URL fetching

Always use `url_helper.readurl()` or `url_helper.wait_for_url()` — never `urllib`
directly.

```python
from cloudinit import url_helper

resp = url_helper.readurl(url, headers=HEADERS, timeout=10, retries=3)
url, resp = url_helper.wait_for_url(
    urls=[METADATA_URL],
    max_wait=120,
    timeout=10,
    status_cb=LOG.warning,
)
```

`readurl()` is at `url_helper.py:451`; `wait_for_url()` is at `url_helper.py:737`.
Always set a `timeout`; never leave it at `None` for production paths.

## Shared helpers pointer

`cloudinit/.kb/core-modules.md` covers `url_helper` and `util` in detail.
