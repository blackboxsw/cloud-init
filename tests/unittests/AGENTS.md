## tests/unittests — unit tests

Unit tests live under `tests/unittests/` and mirror the `cloudinit/`
directory structure.

Full reference: tests/unittests/.kb/testing.md

### Rules

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
