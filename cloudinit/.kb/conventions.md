# Code Conventions

## Formatting

| Tool | Setting | Config location |
|------|---------|----------------|
| black | line-length = 79 | `pyproject.toml:6` |
| ruff | line-length = 79 | `pyproject.toml:180` |
| isort | profile = "black", line_length = 79 | `pyproject.toml:9` |
| shfmt | `--case-indent --indent=4 --space-redirects` | `tox.ini:110` (applied to `./tools/`) |
| JSON schemas | `python3 -m json.tool --indent 2` | manual before committing |

## Type annotations

Required for all new code under `cloudinit/`. mypy is enforced (`pyproject.toml:15`):
`check_untyped_defs = true`, `warn_redundant_casts = true`, `warn_unused_ignores = true`.

## Comments

Only when the WHY is non-obvious: a hidden constraint, a workaround, a subtle
invariant. No docstrings that restate what the function name already says.

## `subp` over stdlib

Always use `cloudinit.subp.subp()` instead of `subprocess` directly. This ensures
uniform logging, error handling, and test intercept via `disable_subp_usage`.

## `util` over stdlib

Prefer these wrappers over direct `open()` / `os` calls:

| Wrapper | Location | Use instead of |
|---------|----------|---------------|
| `util.write_file()` | `util.py:2243` | `open(path, "w")` |
| `util.load_text_file()` | `util.py` | `open(path).read()` |
| `util.get_cfg_option_str()` | `util.py:491` | `cfg.get("key")` |
| `util.get_cfg_option_list()` | `util.py:669` | `cfg.get("key", [])` |
| `util.get_cfg_option_bool()` | `util.py:485` | `bool(cfg.get("key"))` |

## tox environment reference

| Environment | Purpose | When to run |
|-------------|---------|-------------|
| `py3` | Unit tests (pytest) | Before every commit |
| `black` | Formatting check | Before every commit |
| `ruff` | Linting | Before every commit |
| `isort` | Import sort check | Before every commit |
| `mypy` | Type checking | Before every commit |
| `do_format` | Auto-format code in-place | To fix formatting |
| `check_format` | Full formatting validation | CI gate |
| `py3-fast` | Parallel unit tests (xdist) | Quick local iteration |
| `doc` | Sphinx documentation build | When editing docs |
| `integration-tests` | Full integration tests | Pre-release / cloud testing |

Run a single environment: `tox -e py3`. Run a single test file:
`tox -e py3 -- tests/unittests/config/test_cc_ntp.py`.
