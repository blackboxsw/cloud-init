# This file is part of cloud-init. See LICENSE file for license information.

"""Tests for tools.integration_dashboard.

All tests are hermetic: no network, tmp_path only, API mocked.
"""

import io
import zipfile
from pathlib import Path
from unittest import mock

import pytest

from tools import integration_dashboard as dash

FIXTURES = Path(__file__).parent.parent / "data" / "integration_dashboard"


def read_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class TestParseJunit:
    """V1: JUnit parsing with various fixtures."""

    def test_all_pass(self):
        results = dash.parse_junit(read_fixture("all_pass.xml"))
        assert len(results) == 3
        assert all(r.outcome == "P" for r in results)

    def test_failure(self):
        results = dash.parse_junit(read_fixture("mixed_outcomes.xml"))
        fail = [r for r in results if r.nodeid.endswith("test_defaults")]
        assert len(fail) == 1
        assert fail[0].outcome == "F"

    def test_error(self):
        results = dash.parse_junit(read_fixture("mixed_outcomes.xml"))
        err = [r for r in results if r.nodeid.endswith("test_sources_list")]
        assert len(err) == 1
        assert err[0].outcome == "E"

    def test_skipped(self):
        results = dash.parse_junit(read_fixture("mixed_outcomes.xml"))
        skip = [r for r in results if r.nodeid.endswith("test_ppa_source")]
        assert len(skip) == 1
        assert skip[0].outcome == "S"

    def test_xfail(self):
        results = dash.parse_junit(read_fixture("parametrized.xml"))
        xfail = [r for r in results if "key2" in r.nodeid]
        assert len(xfail) == 1
        assert xfail[0].outcome == "X"

    def test_parametrized_name(self):
        results = dash.parse_junit(read_fixture("parametrized.xml"))
        assert any("test_keys[rsa-key1]" in r.nodeid for r in results)

    def test_multi_suite(self):
        results = dash.parse_junit(read_fixture("multi_suite.xml"))
        assert len(results) == 3

    def test_zero_tests(self):
        results = dash.parse_junit(read_fixture("zero_tests.xml"))
        assert len(results) == 0

    def test_doctype_rejected(self):
        with pytest.raises(ValueError, match="DOCTYPE"):
            dash.parse_junit(read_fixture("with_doctype.xml"))

    def test_malformed_xml(self):
        with pytest.raises(ValueError, match="malformed"):
            dash.parse_junit(b"<not-closed>")

    def test_nodeid_property_preferred(self):
        results = dash.parse_junit(read_fixture("with_nodeid_property.xml"))
        assert results[0].nodeid == (
            "tests/integration_tests/test_paths.py"
            "::TestHonorCloudDir::test_honor_cloud_dir"
        )
        assert results[1].nodeid == (
            "tests/integration_tests/test_defaults.py::test_defaults"
        )


class TestNodeidReconstruction:
    """V2: Node-id round-trip against the real suite."""

    def test_simple_class(self):
        nid = dash.reconstruct_nodeid(
            "tests.integration_tests.test_paths.TestHonorCloudDir",
            "test_honor_cloud_dir",
        )
        assert nid == (
            "tests/integration_tests/test_paths.py"
            "::TestHonorCloudDir::test_honor_cloud_dir"
        )

    def test_no_class(self):
        nid = dash.reconstruct_nodeid(
            "tests.integration_tests.test_defaults",
            "test_defaults",
        )
        assert nid == (
            "tests/integration_tests/test_defaults.py::test_defaults"
        )

    def test_nested_dir(self):
        nid = dash.reconstruct_nodeid(
            "tests.integration_tests.cmd.test_clean.TestClean",
            "test_clean",
        )
        assert nid == (
            "tests/integration_tests/cmd/test_clean.py"
            "::TestClean::test_clean"
        )

    def test_parametrized(self):
        nid = dash.reconstruct_nodeid(
            "tests.integration_tests.modules.test_apt.TestApt",
            "test_sources_list[a-b]",
        )
        assert nid == (
            "tests/integration_tests/modules/test_apt.py"
            "::TestApt::test_sources_list[a-b]"
        )

    def test_heuristics_agree_on_real_suite(self):
        """Both heuristics must agree on every real test file."""
        import ast

        tests_root = Path(__file__).parent.parent.parent
        integration_dir = tests_root / "tests" / "integration_tests"
        checked = 0
        for py_file in sorted(integration_dir.rglob("test_*.py")):
            rel = py_file.relative_to(tests_root)
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if isinstance(
                            child, ast.FunctionDef
                        ) and child.name.startswith("test_"):
                            nodeid = f"{rel}::{node.name}::{child.name}"
                            names = dash.mangle_test_address(nodeid)
                            classname = ".".join(names[:-1])
                            segs = classname.split(".")
                            pa, _ = dash._split_heuristic_test_prefix(segs)
                            pb, _ = dash._split_heuristic_uppercase(segs)
                            assert pa == pb, f"heuristic mismatch for {nodeid}"
                            checked += 1
        assert checked > 100

    def test_mangle_round_trip(self):
        nodeid = (
            "tests/integration_tests/modules/test_apt.py"
            "::TestApt::test_sources_list[a-b]"
        )
        names = dash.mangle_test_address(nodeid)
        classname = ".".join(names[:-1])
        name = names[-1]
        assert dash.reconstruct_nodeid(classname, name) == nodeid


class TestInfraClassification:
    """V5: Infra-failure classification."""

    def test_zero_testcases_is_infra(self):
        parsed = dash.parse_junit(read_fixture("zero_tests.xml"))
        assert dash.is_infra_failure(parsed, False, 0) is True

    def test_missing_artifact_is_infra(self):
        assert dash.is_infra_failure([], True, 0) is True

    def test_low_count_is_infra(self):
        parsed = dash.parse_junit(read_fixture("all_pass.xml"))
        assert dash.is_infra_failure(parsed, False, 100) is True

    def test_normal_run_not_infra(self):
        parsed = dash.parse_junit(read_fixture("all_pass.xml"))
        assert dash.is_infra_failure(parsed, False, 0) is False

    def test_normal_run_not_infra_with_median(self):
        parsed = dash.parse_junit(read_fixture("all_pass.xml"))
        assert dash.is_infra_failure(parsed, False, 3) is False


class TestStorageAndIdempotency:
    """V4 + V6: Storage, idempotency, and schema evolution."""

    def _ingest(self, tmp_path, fixture_name, run_id=100, **kwargs):
        defaults = dict(
            platform="lxd_container",
            release="jammy",
            version="22.04",
            image_type="generic",
            workflow="110-daily-integration-22.04-lxd_container.yml",
            event="schedule",
            timestamp="2026-08-01T06:17:00Z",
            sha="abc123",
            conclusion="success",
            run_id=run_id,
            attempt=1,
        )
        defaults.update(kwargs)
        data_dir = tmp_path / "ci-dashboard" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        junit_path = FIXTURES / fixture_name
        args = mock.Mock(
            data_dir=str(data_dir),
            junit=str(junit_path),
            meta="",
            **defaults,
        )
        return dash.cmd_ingest(args), data_dir

    def test_ingest_creates_files(self, tmp_path):
        _, data_dir = self._ingest(tmp_path, "all_pass.xml")
        assert (data_dir / "tests.json").exists()
        assert (data_dir / "runs" / "2026-08.json").exists()
        assert (data_dir / "index.json").exists()
        assert (data_dir / "summary.json").exists()
        assert (data_dir / "state.json").exists()

    def test_ingest_twice_idempotent(self, tmp_path):
        _, data_dir = self._ingest(tmp_path, "all_pass.xml", run_id=200)
        tests_before = dash.load_tests(data_dir)
        _, data_dir = self._ingest(tmp_path, "all_pass.xml", run_id=200)
        tests_after = dash.load_tests(data_dir)
        assert tests_before == tests_after
        shard = dash.load_json(data_dir / "runs" / "2026-08.json")
        assert len(shard["runs"]) == 1

    def test_second_run_appends(self, tmp_path):
        _, data_dir = self._ingest(tmp_path, "all_pass.xml", run_id=300)
        _, data_dir = self._ingest(tmp_path, "mixed_outcomes.xml", run_id=301)
        shard = dash.load_json(data_dir / "runs" / "2026-08.json")
        assert len(shard["runs"]) == 2

    def test_run_attempt_replaces(self, tmp_path):
        _, data_dir = self._ingest(
            tmp_path,
            "all_pass.xml",
            run_id=400,
            attempt=1,
            conclusion="failure",
        )
        _, data_dir = self._ingest(
            tmp_path,
            "all_pass.xml",
            run_id=400,
            attempt=2,
            conclusion="success",
        )
        shard = dash.load_json(data_dir / "runs" / "2026-08.json")
        assert len(shard["runs"]) == 1
        assert shard["runs"][0]["att"] == 2
        assert shard["runs"][0]["concl"] == "success"

    def test_schema_evolution_right_pad(self, tmp_path):
        _, data_dir = self._ingest(tmp_path, "all_pass.xml", run_id=500)
        tests = dash.load_tests(data_dir)
        tests["ids"].append("new_test_id")
        dash.save_tests(data_dir, tests)
        dash.cmd_summarize_impl(data_dir)
        summary = dash.load_json(data_dir / "summary.json")
        assert len(summary["tests"]) == len(tests["ids"])
        shard = dash.load_json(data_dir / "runs" / "2026-08.json")
        for run in shard["runs"]:
            assert len(run["o"]) <= len(tests["ids"])

    def test_outcome_string_aligned(self, tmp_path):
        _, data_dir = self._ingest(tmp_path, "mixed_outcomes.xml", run_id=600)
        tests = dash.load_tests(data_dir)
        shard = dash.load_json(data_dir / "runs" / "2026-08.json")
        run = shard["runs"][0]
        assert len(run["o"]) == len(tests["ids"])
        assert run["n"] == 4


class TestValidate:
    """V10: Validate invariants."""

    def test_valid_data_passes(self, tmp_path):
        _, data_dir = self._setup_data(tmp_path)
        dash.validate(data_dir)

    def test_duplicate_run_id_rejected(self, tmp_path):
        _, data_dir = self._setup_data(tmp_path)
        shard_path = data_dir / "runs" / "2026-08.json"
        shard = dash.load_json(shard_path)
        shard["runs"].append(shard["runs"][0])
        dash.save_json(shard_path, shard)
        with pytest.raises(ValueError, match="duplicate run"):
            dash.validate(data_dir)

    def test_unknown_outcome_rejected(self, tmp_path):
        _, data_dir = self._setup_data(tmp_path)
        shard_path = data_dir / "runs" / "2026-08.json"
        shard = dash.load_json(shard_path)
        shard["runs"][0]["o"] = "ZZZZ"
        dash.save_json(shard_path, shard)
        with pytest.raises(ValueError, match="unknown outcome"):
            dash.validate(data_dir)

    def test_outcome_too_long_rejected(self, tmp_path):
        _, data_dir = self._setup_data(tmp_path)
        shard_path = data_dir / "runs" / "2026-08.json"
        shard = dash.load_json(shard_path)
        shard["runs"][0]["o"] = "P" * 999
        dash.save_json(shard_path, shard)
        with pytest.raises(ValueError, match="longer than"):
            dash.validate(data_dir)

    def _setup_data(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dash.save_tests(
            data_dir,
            {"schema_version": 1, "ids": ["test_a", "test_b"]},
        )
        dash.save_json(
            data_dir / "runs" / "2026-08.json",
            {
                "schema_version": 1,
                "month": "2026-08",
                "runs": [
                    {
                        "id": 1,
                        "wf": "test.yml",
                        "p": "lxd_container",
                        "r": "jammy",
                        "v": "22.04",
                        "it": "generic",
                        "src": "",
                        "ev": "schedule",
                        "t": "2026-08-01T06:00:00Z",
                        "sha": "",
                        "concl": "success",
                        "att": 1,
                        "n": 2,
                        "infra": False,
                        "o": "PP",
                    }
                ],
            },
        )
        dash.save_json(
            data_dir / "index.json",
            {
                "schema_version": 1,
                "platforms": ["lxd_container"],
                "releases": [{"codename": "jammy", "version": "22.04"}],
                "image_types": ["generic"],
                "months": ["2026-08"],
                "archived_months": [],
                "workflows": [],
                "counts": {"total_runs": 1, "total_tests": 2},
            },
        )
        dash.cmd_summarize_impl(data_dir)
        return None, data_dir


class TestAzureGenericity:
    """V8 + V9: Azure auto-discovery and codename self-learning."""

    def test_workflow_regex_matches_azure(self):
        match = dash.WORKFLOW_RE.match(
            ".github/workflows/141-daily-integration-26.04-azure.yml"
        )
        assert match is not None
        assert match.group("platform") == "azure"
        assert match.group("version") == "26.04"

    def test_workflow_regex_excludes_non_integration(self):
        assert (
            dash.WORKFLOW_RE.match(".github/workflows/100-dispatch-common.yml")
            is None
        )
        assert (
            dash.WORKFLOW_RE.match(".github/workflows/21-pr-check-format.yml")
            is None
        )

    def test_azure_appears_in_index(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dash.save_tests(
            data_dir,
            {
                "schema_version": 1,
                "ids": ["test_a"],
            },
        )
        dash.save_json(
            data_dir / "runs" / "2026-08.json",
            {
                "schema_version": 1,
                "month": "2026-08",
                "runs": [
                    {
                        "id": 1,
                        "wf": "141-daily-integration-26.04-azure.yml",
                        "p": "azure",
                        "r": "resolute",
                        "v": "26.04",
                        "it": "generic",
                        "src": "",
                        "ev": "schedule",
                        "t": "2026-08-01T06:00:00Z",
                        "sha": "",
                        "concl": "success",
                        "att": 1,
                        "n": 1,
                        "infra": False,
                        "o": "P",
                    }
                ],
            },
        )
        state = dash.load_state(data_dir)
        all_runs = dash.load_all_runs(data_dir)
        index = dash.update_index(data_dir, all_runs, state)
        assert "azure" in index["platforms"]
        releases = [(r["codename"], r["version"]) for r in index["releases"]]
        assert ("resolute", "26.04") in releases

    def test_no_hardcoded_azure_in_source(self):
        source = (
            Path(__file__)
            .parent.parent.parent.joinpath("tools", "integration_dashboard.py")
            .read_text()
        )
        assert '"azure"' not in source
        assert "'azure'" not in source


class TestHttpLayer:
    """V11: HTTP layer with fake opener."""

    def test_redirect_strips_authorization(self):
        handler = dash._AuthStrippingRedirectHandler()
        req = mock.Mock()
        req.headers = {
            "Authorization": "Bearer secret",
            "Accept": "application/json",
        }
        req.get_method.return_value = "GET"
        req.origin_req_host = "example.com"
        with mock.patch.object(
            dash.urllib.request.HTTPRedirectHandler,
            "redirect_request",
            return_value=dash.urllib.request.Request(
                "https://blob.example.com/data",
                headers={
                    "Authorization": "Bearer secret",
                    "Accept": "application/json",
                },
            ),
        ):
            result = handler.redirect_request(
                req, None, 302, "Found", {}, "https://blob.example.com"
            )
        assert result.get_header("Authorization") is None
        assert result.get_header("Accept") == "application/json"

    def test_parse_next_link(self):
        link = (
            '<https://api.github.com/page2>; rel="next",'
            ' <https://api.github.com/page1>; rel="prev"'
        )
        assert dash._parse_next_link(link) == ("https://api.github.com/page2")

    def test_parse_next_link_empty(self):
        assert dash._parse_next_link("") == ""

    def test_rate_limit_floor_stops(self, tmp_path):
        client = dash.GitHubClient("fake-token")
        client.remaining = 10
        assert client.rate_limit_ok() is False

    def test_rate_limit_ok_when_above_floor(self):
        client = dash.GitHubClient("fake-token")
        client.remaining = 100
        assert client.rate_limit_ok() is True


class TestArtifactExtraction:
    """V11: Artifact zip extraction with size caps."""

    def test_extract_junit_from_zip(self):
        xml = (
            b'<?xml version="1.0"?>'
            b"<testsuites><testsuite>"
            b'<testcase classname="a" name="b"/>'
            b"</testsuite></testsuites>"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("junit-report.xml", xml)
        result = dash.extract_junit_from_zip(buf.getvalue())
        assert b"testcase" in result

    def test_extract_rejects_zip_bomb(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "junit.xml",
                b"<x>" * (dash.MAX_XML_BYTES + 1),
            )
        with pytest.raises(ValueError, match="exceeds"):
            dash.extract_junit_from_zip(buf.getvalue())


class TestRollup:
    """V10: Rollup correctness."""

    def test_rollup_archives_old_shard(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dash.save_tests(
            data_dir,
            {"schema_version": 1, "ids": ["test_a"]},
        )
        old_ts = "2025-01-15T06:00:00Z"
        dash.save_json(
            data_dir / "runs" / "2025-01.json",
            {
                "schema_version": 1,
                "month": "2025-01",
                "runs": [
                    {
                        "id": 1,
                        "wf": "test.yml",
                        "p": "lxd_container",
                        "r": "jammy",
                        "v": "22.04",
                        "it": "generic",
                        "src": "",
                        "ev": "schedule",
                        "t": old_ts,
                        "sha": "",
                        "concl": "success",
                        "att": 1,
                        "n": 1,
                        "infra": False,
                        "o": "P",
                    }
                ],
            },
        )
        args = mock.Mock(
            data_dir=str(data_dir),
            retention_days=30,
        )
        dash.cmd_rollup(args)
        assert not (data_dir / "runs" / "2025-01.json").exists()
        assert (data_dir / "archive" / "2025-01.json").exists()

    def test_rollup_keeps_recent_shard(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dash.save_tests(
            data_dir,
            {"schema_version": 1, "ids": ["test_a"]},
        )
        recent_ts = "2026-07-15T06:00:00Z"
        dash.save_json(
            data_dir / "runs" / "2026-07.json",
            {
                "schema_version": 1,
                "month": "2026-07",
                "runs": [
                    {
                        "id": 1,
                        "wf": "test.yml",
                        "p": "lxd_container",
                        "r": "jammy",
                        "v": "22.04",
                        "it": "generic",
                        "src": "",
                        "ev": "schedule",
                        "t": recent_ts,
                        "sha": "",
                        "concl": "success",
                        "att": 1,
                        "n": 1,
                        "infra": False,
                        "o": "P",
                    }
                ],
            },
        )
        args = mock.Mock(
            data_dir=str(data_dir),
            retention_days=dash.DETAIL_RETENTION_DAYS,
        )
        dash.cmd_rollup(args)
        assert (data_dir / "runs" / "2026-07.json").exists()


class TestCheckNodeidMapping:
    """V3: check-nodeid-mapping subcommand."""

    def test_check_passes_on_real_suite(self):
        args = mock.Mock(tests_dir="tests/integration_tests")
        rc = dash.cmd_check_nodeid_mapping(args)
        assert rc == 0


class TestSummarize:
    """Summarize correctness."""

    def test_summary_has_cells(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dash.save_tests(
            data_dir,
            {"schema_version": 1, "ids": ["test_a", "test_b"]},
        )
        dash.save_json(
            data_dir / "runs" / "2026-08.json",
            {
                "schema_version": 1,
                "month": "2026-08",
                "runs": [
                    {
                        "id": 1,
                        "wf": "test.yml",
                        "p": "lxd_container",
                        "r": "jammy",
                        "v": "22.04",
                        "it": "generic",
                        "src": "",
                        "ev": "schedule",
                        "t": "2026-08-01T06:00:00Z",
                        "sha": "",
                        "concl": "failure",
                        "att": 1,
                        "n": 2,
                        "infra": False,
                        "o": "PF",
                    },
                    {
                        "id": 2,
                        "wf": "test.yml",
                        "p": "lxd_container",
                        "r": "jammy",
                        "v": "22.04",
                        "it": "generic",
                        "src": "",
                        "ev": "schedule",
                        "t": "2026-08-02T06:00:00Z",
                        "sha": "",
                        "concl": "success",
                        "att": 1,
                        "n": 2,
                        "infra": False,
                        "o": "PP",
                    },
                ],
            },
        )
        dash.cmd_summarize_impl(data_dir)
        summary = dash.load_json(data_dir / "summary.json")
        cell = summary["tests"][0]["c"]["lxd_container|jammy"]
        assert cell["p"] == 2
        assert cell["f"] == 0
        assert cell["flips"] == 0
        cell_b = summary["tests"][1]["c"]["lxd_container|jammy"]
        assert cell_b["p"] == 1
        assert cell_b["f"] == 1
        assert cell_b["flips"] == 1

    def test_infra_excluded_from_summary(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dash.save_tests(
            data_dir,
            {"schema_version": 1, "ids": ["test_a"]},
        )
        dash.save_json(
            data_dir / "runs" / "2026-08.json",
            {
                "schema_version": 1,
                "month": "2026-08",
                "runs": [
                    {
                        "id": 1,
                        "wf": "test.yml",
                        "p": "lxd_container",
                        "r": "jammy",
                        "v": "22.04",
                        "it": "generic",
                        "src": "",
                        "ev": "schedule",
                        "t": "2026-08-01T06:00:00Z",
                        "sha": "",
                        "concl": "failure",
                        "att": 1,
                        "n": 0,
                        "infra": True,
                        "o": "",
                    }
                ],
            },
        )
        dash.cmd_summarize_impl(data_dir)
        summary = dash.load_json(data_dir / "summary.json")
        assert summary["tests"][0]["c"] == {}


class TestNoExternalAssets:
    """V7: No external assets in dashboard front-end."""

    DASHBOARD_DIR = Path(__file__).parent.parent.parent / "tools" / "dashboard"

    def test_dashboard_dir_exists(self):
        assert self.DASHBOARD_DIR.exists()

    def test_no_offorigin_script_src(self):
        for ext in ("*.html", "*.js", "*.css"):
            for f in self.DASHBOARD_DIR.glob(ext):
                content = f.read_text()
                assert "http://" not in content, f"{f.name} contains http://"
                if "https://" in content:
                    assert all(
                        url.startswith(
                            "https://github.com/canonical/cloud-init/"
                        )
                        for url in _extract_urls(content)
                        if url
                    ), f"{f.name} contains off-origin https URL"

    def test_csp_meta_present(self):
        html = (self.DASHBOARD_DIR / "index.html").read_text()
        assert "default-src 'none'" in html
        assert "script-src 'self'" in html
        assert "connect-src 'self'" in html

    def test_no_remote_import_or_url(self):
        for f in self.DASHBOARD_DIR.glob("*.css"):
            content = f.read_text()
            assert "@import" not in content or "@import" not in content
        for f in self.DASHBOARD_DIR.glob("*.js"):
            content = f.read_text()
            assert "url(" not in content


def _extract_urls(text):
    import re

    return re.findall(r'https?://[^\s"\'<>)]+', text)
