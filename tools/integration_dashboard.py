#!/usr/bin/env python3
"""Cloud-init integration test results dashboard aggregator.

This stdlib-only module collects scheduled integration-test workflow
results from the GitHub Actions API, parses JUnit XML, and writes
compact JSON shards consumed by the dashboard front end.

Subcommands:
  collect       Fetch runs via the GitHub API, parse, and append.
  summarize     Recompute summary.json from on-disk data.
  rollup        Archive and prune old monthly shards.
  validate      Check storage invariants; exit non-zero on corruption.
  ingest        Offline: ingest one junit+meta pair (no API calls).
  check-nodeid-mapping  Walk the real test tree, assert round-trip.
  serve         Local preview server wrapping http.server.

Security note: xml.etree.ElementTree parses JUnit XML produced by our
own scheduled runs.  Documents containing a DOCTYPE declaration are
rejected (entity-expansion defence) and artifact zip / extracted XML
sizes are capped.  defusedxml is unavailable under the no-dependency
constraint.
"""

import argparse
import dataclasses
import datetime
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# === Constants ===========================================================

SCHEMA_VERSION = 1
DATA_SUBDIR = "ci-dashboard/data"
ASSET_SUBDIR = "ci-dashboard"

OUTCOME_PASS = "P"
OUTCOME_FAIL = "F"
OUTCOME_ERROR = "E"
OUTCOME_SKIP = "S"
OUTCOME_XFAIL = "X"
OUTCOME_ABSENT = "-"
ALL_OUTCOMES = frozenset("PFESX-")

WORKFLOW_RE = re.compile(
    r"^\.github/workflows/\d+-daily-integration-"
    r"(?P<version>\d\d\.\d\d)-(?P<platform>[a-z0-9_]+)\.ya?ml$"
)

FALLBACK_CODENAMES: Dict[str, str] = {
    "22.04": "jammy",
    "24.04": "noble",
    "26.04": "resolute",
    "26.10": "stonking",
}

DEFAULT_OWNER = "canonical"
DEFAULT_REPO = "cloud-init"
DETAIL_RETENTION_DAYS = 120
RATE_LIMIT_FLOOR = 50
MAX_ARTIFACT_ZIP_BYTES = 32 * 1024 * 1024
MAX_XML_BYTES = 64 * 1024 * 1024
MAX_ZIP_MEMBERS = 1000
API_VERSION = "2022-11-28"
USER_AGENT = "cloud-init-integration-dashboard/1.0"


# === Data classes ========================================================


@dataclasses.dataclass
class ParsedTest:
    """A single parsed testcase from JUnit XML."""

    nodeid: str
    outcome: str


@dataclasses.dataclass
class RunRecord:
    """A single integration test run, ready for storage."""

    run_id: int
    workflow: str
    platform: str
    release: str
    version: str
    image_type: str
    install_source: str
    event: str
    timestamp: str
    sha: str
    conclusion: str
    attempt: int
    test_count: int
    infra: bool
    outcomes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.run_id,
            "wf": self.workflow,
            "p": self.platform,
            "r": self.release,
            "v": self.version,
            "it": self.image_type,
            "src": self.install_source,
            "ev": self.event,
            "t": self.timestamp,
            "sha": self.sha,
            "concl": self.conclusion,
            "att": self.attempt,
            "n": self.test_count,
            "infra": self.infra,
            "o": self.outcomes,
        }


# === JSON I/O ============================================================


def load_json(path: Path) -> Any:
    """Load JSON from *path*, returning {} if the file is absent."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: Any) -> None:
    """Atomically write *data* as JSON with deterministic key order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True, indent=1)
        fh.write("\n")
    tmp.replace(path)


def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 with trailing Z."""
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def month_key(timestamp: str) -> str:
    """Extract YYYY-MM from an ISO-8601 timestamp."""
    return timestamp[:7]


# === JUnit parsing =======================================================


def _has_doctype(data: bytes) -> bool:
    stripped = data.lstrip()[:200].lower()
    return b"<!doctype" in stripped


def parse_junit(xml_bytes: bytes) -> List[ParsedTest]:
    """Parse JUnit XML bytes into a list of :class:`ParsedTest`.

    Raises ``ValueError`` on DOCTYPE, oversized XML, or malformed
    content.  Uses ``iterparse`` for bounded memory.
    """
    if _has_doctype(xml_bytes):
        raise ValueError("DOCTYPE declarations are not allowed")
    if len(xml_bytes) > MAX_XML_BYTES:
        raise ValueError(f"XML exceeds {MAX_XML_BYTES} bytes")
    results: List[ParsedTest] = []
    try:
        root_iter = ET.iterparse(io.BytesIO(xml_bytes), events=("end",))
        for _event, elem in root_iter:
            if elem.tag != "testcase":
                continue
            parsed = _parse_testcase(elem)
            if parsed is not None:
                results.append(parsed)
            elem.clear()
    except ET.ParseError as exc:
        raise ValueError(f"malformed XML: {exc}") from exc
    return results


def _parse_testcase(elem: ET.Element) -> Optional[ParsedTest]:
    classname = elem.get("classname", "")
    name = elem.get("name", "")
    if not classname or not name:
        return None
    nodeid = _extract_nodeid(elem, classname, name)
    outcome = _classify_outcome(elem)
    return ParsedTest(nodeid=nodeid, outcome=outcome)


def _extract_nodeid(elem: ET.Element, classname: str, name: str) -> str:
    """Prefer an explicit ``nodeid`` property; fall back to reconstruction."""
    props = elem.find("properties")
    if props is not None:
        for prop in props.findall("property"):
            if prop.get("name") == "nodeid":
                return prop.get("value", "")
    return reconstruct_nodeid(classname, name)


def _classify_outcome(elem: ET.Element) -> str:
    if elem.find("failure") is not None:
        return OUTCOME_FAIL
    if elem.find("error") is not None:
        return OUTCOME_ERROR
    skipped = elem.find("skipped")
    if skipped is not None:
        if skipped.get("type") == "pytest.xfail":
            return OUTCOME_XFAIL
        return OUTCOME_SKIP
    return OUTCOME_PASS


# === Node-id reconstruction ==============================================


def reconstruct_nodeid(classname: str, name: str) -> str:
    """Reconstruct a pytest node id from xunit2 classname + name.

    Uses two heuristics and cross-checks them.  On disagreement the
    node id is bucketed under ``__unreconstructed__`` so the anomaly
    surfaces on the dashboard rather than silently corrupting data.
    """
    segments = classname.split(".")
    path_a, chain_a = _split_heuristic_test_prefix(segments)
    path_b, chain_b = _split_heuristic_uppercase(segments)
    if path_a == path_b and chain_a == chain_b:
        path = path_a
        chain = chain_a
    else:
        return f"__unreconstructed__.{classname}::{name}"
    file_path = "/".join(path) + ".py"
    parts: List[str] = [file_path]
    parts.extend(chain)
    parts.append(name)
    return "::".join(parts)


def _split_heuristic_test_prefix(
    segments: Sequence[str],
) -> Tuple[List[str], List[str]]:
    """Heuristic A: path up to and including first ``test_*`` segment."""
    for i, seg in enumerate(segments):
        if seg.startswith("test_"):
            return list(segments[: i + 1]), list(segments[i + 1 :])
    return list(segments), []


def _split_heuristic_uppercase(
    segments: Sequence[str],
) -> Tuple[List[str], List[str]]:
    """Heuristic B: path before first uppercase-initial segment."""
    for i, seg in enumerate(segments):
        if seg and seg[0].isupper():
            return list(segments[:i]), list(segments[i:])
    return list(segments), []


def mangle_test_address(address: str) -> List[str]:
    """Replicate pytest's ``mangle_test_address`` for round-trip tests.

    This mirrors ``_pytest.junitxml.mangle_test_address`` so the
    ``check-nodeid-mapping`` subcommand can work without importing
    pytest internals.
    """
    path, bracket, params = address.partition("[")
    names = path.split("::")
    names[0] = names[0].replace("/", ".")
    names[0] = re.sub(r"\.py$", "", names[0])
    names[-1] += bracket + params
    return names


# === Infra-failure classification ========================================


def is_infra_failure(
    parsed: Sequence[ParsedTest],
    artifact_missing: bool,
    median_count: int,
) -> bool:
    """Classify a run as an infrastructure failure.

    A run is infra if the artifact is missing, if zero testcases
    were collected, or if the test count is below 25% of the median
    for the same (platform, release) over recent good runs.
    """
    if artifact_missing:
        return True
    if len(parsed) == 0:
        return True
    if median_count > 0 and len(parsed) < median_count * 0.25:
        return True
    return False


def compute_median(values: Sequence[int]) -> int:
    if not values:
        return 0
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) // 2
    return sorted_vals[mid]


# === GitHub API client ===================================================


class _AuthStrippingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Strip the Authorization header when following redirects.

    GitHub artifact downloads 302-redirect to signed blob URLs that
    reject a forwarded Authorization header with 400/403.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result is not None:
            result.remove_header("Authorization")
        return result


class GitHubClient:
    """Minimal GitHub REST API client on urllib.request."""

    def __init__(
        self,
        token: str,
        owner: str = DEFAULT_OWNER,
        repo: str = DEFAULT_REPO,
    ) -> None:
        self.token = token
        self.base = f"https://api.github.com/repos/{owner}/{repo}/actions"
        self.api_root = f"https://api.github.com/repos/{owner}/{repo}"
        self.opener = urllib.request.build_opener(
            _AuthStrippingRedirectHandler()
        )
        self.remaining: Optional[int] = None

    def _request(
        self, url: str, method: str = "GET"
    ) -> Tuple[bytes, Dict[str, str]]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }
        req = urllib.request.Request(url, headers=headers, method=method)
        for attempt in range(4):
            try:
                resp = self.opener.open(req, timeout=60)
                body = resp.read()
                remaining = resp.headers.get("X-RateLimit-Remaining")
                if remaining is not None:
                    self.remaining = int(remaining)
                return body, dict(resp.headers)
            except urllib.error.HTTPError as exc:
                if exc.code == 403:
                    remaining = exc.headers.get("X-RateLimit-Remaining")
                    if remaining is not None:
                        self.remaining = int(remaining)
                    if (
                        self.remaining is not None
                        and self.remaining <= RATE_LIMIT_FLOOR
                    ):
                        raise
                if exc.code in (429, 500, 502, 503, 504):
                    wait = 2**attempt
                    time.sleep(wait)
                    continue
                raise
            except urllib.error.URLError:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
        raise RuntimeError("max retries exceeded")

    def get_json(self, path: str) -> Any:
        url = path if path.startswith("http") else f"{self.api_root}{path}"
        body, _headers = self._request(url)
        return json.loads(body)

    def get_pages(self, path: str) -> List[Any]:
        url = path if path.startswith("http") else f"{self.api_root}{path}"
        results: List[Any] = []
        while url:
            body, headers = self._request(url)
            page = json.loads(body)
            if isinstance(page, list):
                results.extend(page)
            elif isinstance(page, dict) and "items" in page:
                results.extend(page["items"])
            else:
                results.append(page)
            link = headers.get("Link", "")
            url = _parse_next_link(link)
            if self.remaining is not None and self.remaining <= 0:
                break
        return results

    def rate_limit_ok(self) -> bool:
        if self.remaining is None:
            return True
        return self.remaining > RATE_LIMIT_FLOOR

    def download_artifact(self, url: str) -> bytes:
        """Download and return raw artifact zip bytes (size-capped)."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        resp = self.opener.open(req, timeout=120)
        buf = io.BytesIO()
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            buf.write(chunk)
            if buf.tell() > MAX_ARTIFACT_ZIP_BYTES:
                raise ValueError(
                    f"artifact zip exceeds {MAX_ARTIFACT_ZIP_BYTES} bytes"
                )
        return buf.getvalue()


def _parse_next_link(link_header: str) -> str:
    if not link_header:
        return ""
    for part in link_header.split(","):
        segs = part.strip().split(";")
        if len(segs) < 2:
            continue
        url = segs[0].strip().strip("<>")
        for seg in segs[1:]:
            if 'rel="next"' in seg:
                return url
    return ""


def extract_junit_from_zip(zip_bytes: bytes) -> bytes:
    """Extract and return the JUnit XML from an artifact zip."""
    bio = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(bio) as zf:
        members = zf.namelist()
        if len(members) > MAX_ZIP_MEMBERS:
            raise ValueError(f"zip has too many members: {len(members)}")
        xml_name = ""
        for name in members:
            if name.endswith(".xml") and "junit" in name.lower():
                xml_name = name
                break
        if not xml_name:
            for name in members:
                if name.endswith(".xml"):
                    xml_name = name
                    break
        if not xml_name:
            raise ValueError("no XML file found in artifact zip")
        data = zf.read(xml_name)
        if len(data) > MAX_XML_BYTES:
            raise ValueError(f"extracted XML exceeds {MAX_XML_BYTES} bytes")
        return data


# === Workflow discovery ==================================================


def discover_workflows(
    client: GitHubClient,
    workflow_pattern: str = "",
) -> List[Dict[str, str]]:
    """Discover integration workflows by filename regex."""
    regex = re.compile(workflow_pattern) if workflow_pattern else WORKFLOW_RE
    workflows: List[Dict[str, str]] = []
    page = 1
    while True:
        data = client.get_json(f"/actions/workflows?per_page=100&page={page}")
        items = data.get("workflows", []) if isinstance(data, dict) else []
        if not items:
            break
        for wf in items:
            path = wf.get("path", "")
            match = regex.match(path)
            if match:
                workflows.append(
                    {
                        "id": wf.get("id"),
                        "path": path,
                        "version": match.group("version"),
                        "platform": match.group("platform"),
                        "name": wf.get("name", ""),
                    }
                )
        if len(items) < 100:
            break
        page += 1
    return workflows


# === Storage operations ==================================================


def data_dir_of(root: Path) -> Path:
    return root / DATA_SUBDIR


def load_tests(data_dir: Path) -> Dict[str, Any]:
    return load_json(data_dir / "tests.json")


def save_tests(data_dir: Path, tests: Dict[str, Any]) -> None:
    save_json(data_dir / "tests.json", tests)


def intern_nodeids(data_dir: Path, nodeids: Sequence[str]) -> Dict[str, int]:
    """Intern node ids into tests.json, returning a name->index map."""
    tests = load_tests(data_dir)
    if not tests:
        tests = {"schema_version": SCHEMA_VERSION, "ids": []}
    index_map: Dict[str, int] = {}
    changed = False
    for i, nid in enumerate(tests["ids"]):
        index_map[nid] = i
    for nid in nodeids:
        if nid not in index_map:
            index_map[nid] = len(tests["ids"])
            tests["ids"].append(nid)
            changed = True
    if changed:
        save_tests(data_dir, tests)
    return index_map


def build_outcome_string(
    parsed: Sequence[ParsedTest],
    index_map: Dict[str, int],
    total_ids: int,
) -> str:
    """Build the one-char-per-test outcome string."""
    chars = [OUTCOME_ABSENT] * total_ids
    for pt in parsed:
        idx = index_map.get(pt.nodeid)
        if idx is not None and idx < len(chars):
            chars[idx] = pt.outcome
    return "".join(chars)


def append_run(data_dir: Path, run: RunRecord) -> None:
    """Append or replace a run record in its monthly shard."""
    shard_path = data_dir / "runs" / f"{month_key(run.timestamp)}.json"
    shard = load_json(shard_path)
    if not shard:
        shard = {
            "schema_version": SCHEMA_VERSION,
            "month": month_key(run.timestamp),
            "runs": [],
        }
    runs = shard.get("runs", [])
    for i, existing in enumerate(runs):
        if existing.get("id") == run.run_id:
            if run.attempt >= existing.get("att", 0):
                runs[i] = run.to_dict()
                shard["runs"] = runs
                save_json(shard_path, shard)
            return
    runs.append(run.to_dict())
    shard["runs"] = runs
    save_json(shard_path, shard)


def load_state(data_dir: Path) -> Dict[str, Any]:
    state = load_json(data_dir / "state.json")
    if not state:
        state = {
            "last_scan": "",
            "processed": [],
            "skipped": [],
            "codename_versions": {},
            "aggregator_version": SCHEMA_VERSION,
        }
    return state


def save_state(data_dir: Path, state: Dict[str, Any]) -> None:
    save_json(data_dir / "state.json", state)


def load_all_runs(data_dir: Path) -> List[Dict[str, Any]]:
    """Load all run records from monthly shards."""
    runs_dir = data_dir / "runs"
    if not runs_dir.exists():
        return []
    all_runs: List[Dict[str, Any]] = []
    for shard_path in sorted(runs_dir.glob("*.json")):
        shard = load_json(shard_path)
        all_runs.extend(shard.get("runs", []))
    return all_runs


def update_index(
    data_dir: Path,
    runs: Sequence[Dict[str, Any]],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Rebuild index.json from observed data."""
    platforms: set = set()
    releases: Dict[str, str] = {}
    image_types: set = set()
    months: set = set()
    wf_map: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        p = run.get("p", "")
        r = run.get("r", "")
        v = run.get("v", "")
        it = run.get("it", "")
        wf = run.get("wf", "")
        ts = run.get("t", "")
        if p:
            platforms.add(p)
        if r and v:
            releases[r] = v
            if "codename_versions" not in state:
                state["codename_versions"] = {}
            state["codename_versions"][r] = v
        if it:
            image_types.add(it)
        if ts:
            months.add(month_key(ts))
        if wf:
            if wf not in wf_map:
                wf_map[wf] = {
                    "path": wf,
                    "platform": p,
                    "version": v,
                    "last_run": ts,
                    "last_conclusion": run.get("concl", ""),
                    "infra_failures_30d": 0,
                }
            else:
                if ts > wf_map[wf]["last_run"]:
                    wf_map[wf]["last_run"] = ts
                    wf_map[wf]["last_conclusion"] = run.get("concl", "")
            if run.get("infra"):
                wf_map[wf]["infra_failures_30d"] += 1
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=30)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    for wf_info in wf_map.values():
        recent_infra = sum(
            1
            for r in runs
            if r.get("wf") == wf_info["path"]
            and r.get("infra")
            and r.get("t", "") >= cutoff
        )
        wf_info["infra_failures_30d"] = recent_infra
    index = {
        "schema_version": SCHEMA_VERSION,
        "platforms": sorted(platforms),
        "releases": [
            {"codename": k, "version": v} for k, v in sorted(releases.items())
        ],
        "image_types": sorted(image_types),
        "months": sorted(months),
        "archived_months": sorted(
            [p.stem for p in (data_dir / "archive").glob("*.json")]
            if (data_dir / "archive").exists()
            else []
        ),
        "workflows": sorted(wf_map.values(), key=lambda w: w["path"]),
        "counts": {
            "total_runs": len(runs),
            "total_tests": len(load_tests(data_dir).get("ids", [])),
        },
    }
    save_json(data_dir / "index.json", index)
    return index


# === Median computation for infra classification ========================


def compute_medians(
    runs: Sequence[Dict[str, Any]],
) -> Dict[str, int]:
    """Compute median test count per (platform, release)."""
    buckets: Dict[str, List[int]] = {}
    for run in runs:
        if run.get("infra"):
            continue
        key = f"{run.get('p', '')}|{run.get('r', '')}"
        buckets.setdefault(key, []).append(run.get("n", 0))
    return {k: compute_median(v) for k, v in buckets.items()}


# === Collect command =====================================================


def cmd_collect(args: argparse.Namespace) -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN is required for collect", file=sys.stderr)
        return 1
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    client = GitHubClient(token, args.owner, args.repo)
    state = load_state(data_dir)
    processed = set(state.get("processed", []))
    workflows = discover_workflows(client, args.workflow_pattern)
    print(f"Discovered {len(workflows)} workflows")
    since = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=args.since_days)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = load_all_runs(data_dir)
    medians = compute_medians(runs)
    ingested = 0
    skipped = 0
    for wf in workflows:
        if not client.rate_limit_ok():
            print(
                f"Rate limit floor reached ({client.remaining} remaining),"
                " stopping cleanly"
            )
            state["last_scan"] = utc_now_iso()
            save_state(data_dir, state)
            break
        wf_runs = _fetch_workflow_runs(
            client, wf["id"], since, args.include_manual
        )
        for run_info in wf_runs:
            run_id = int(run_info.get("id", 0))
            if run_id in processed:
                continue
            artifact_data = _find_junit_artifact(
                client, run_id, state, run_info
            )
            artifact_missing = artifact_data is None
            parsed: List[ParsedTest] = []
            if artifact_data is not None:
                try:
                    xml_bytes = extract_junit_from_zip(artifact_data)
                    parsed = parse_junit(xml_bytes)
                except ValueError as exc:
                    print(
                        f"  run {run_id}: parse error: {exc}",
                        file=sys.stderr,
                    )
                    artifact_missing = True
            median_key = f"{wf['platform']}|{run_info.get('release', '')}"
            release = _extract_release_from_artifact(run_info, wf)
            median_key = f"{wf['platform']}|{release}"
            infra = is_infra_failure(
                parsed,
                artifact_missing,
                medians.get(median_key, 0),
            )
            nodeids = [pt.nodeid for pt in parsed]
            index_map = intern_nodeids(data_dir, nodeids)
            tests = load_tests(data_dir)
            total_ids = len(tests.get("ids", []))
            outcome_str = build_outcome_string(parsed, index_map, total_ids)
            record = RunRecord(
                run_id=run_id,
                workflow=wf["path"],
                platform=wf["platform"],
                release=release,
                version=wf["version"],
                image_type=_extract_image_type(run_info),
                install_source=run_info.get("install_source", ""),
                event=run_info.get("event", ""),
                timestamp=run_info.get("run_started_at", utc_now_iso()),
                sha=run_info.get("head_sha", ""),
                conclusion=run_info.get("conclusion", ""),
                attempt=run_info.get("run_attempt", 1),
                test_count=len(parsed),
                infra=infra,
                outcomes=outcome_str,
            )
            if args.dry_run:
                print(f"  [dry-run] would ingest run {run_id}")
            else:
                append_run(data_dir, record)
            processed.add(run_id)
            ingested += 1
            if artifact_missing and not infra:
                skipped += 1
    state["processed"] = sorted(processed)
    state["last_scan"] = utc_now_iso()
    if not args.dry_run:
        save_state(data_dir, state)
        all_runs = load_all_runs(data_dir)
        update_index(data_dir, all_runs, state)
        cmd_summarize_impl(data_dir)
        validate(data_dir)
    print(f"Ingested {ingested} runs, skipped {skipped}")
    if client.remaining is not None:
        print(f"API quota remaining: {client.remaining}")
    return 0


def _fetch_workflow_runs(
    client: GitHubClient,
    wf_id: Any,
    since: str,
    include_manual: bool,
) -> List[Dict[str, Any]]:
    runs = client.get_pages(
        f"/actions/workflows/{wf_id}/runs?status=completed"
        f"&per_page=100&created=>={since}"
    )
    result: List[Dict[str, Any]] = []
    for run in runs:
        if run.get("head_branch") != "main":
            continue
        event = run.get("event", "")
        if event != "schedule" and not include_manual:
            continue
        result.append(run)
    return result


def _find_junit_artifact(
    client: GitHubClient,
    run_id: int,
    state: Dict[str, Any],
    run_info: Dict[str, Any],
) -> Optional[bytes]:
    artifacts = client.get_pages(f"/actions/runs/{run_id}/artifacts")
    for art in artifacts:
        name = art.get("name", "")
        if not name.startswith("junit-"):
            continue
        if art.get("expired"):
            state.setdefault("skipped", []).append(
                {"run": run_id, "reason": "expired"}
            )
            continue
        url = art.get("archive_download_url", "")
        if not url:
            continue
        return client.download_artifact(url)
    return None


def _extract_release_from_artifact(
    run_info: Dict[str, Any], wf: Dict[str, str]
) -> str:
    for art in run_info.get("artifacts", []):
        name = art.get("name", "")
        if name.startswith("junit-"):
            parts = name.split("-")
            if len(parts) >= 3:
                return parts[2]
    return FALLBACK_CODENAMES.get(wf["version"], wf["version"])


def _extract_image_type(run_info: Dict[str, Any]) -> str:
    for art in run_info.get("artifacts", []):
        name = art.get("name", "")
        if name.startswith("junit-"):
            parts = name.split("-")
            if len(parts) >= 4:
                return parts[3]
    return "generic"


# === Summarize command ===================================================


def cmd_summarize_impl(data_dir: Path) -> None:
    """Recompute summary.json from on-disk data."""
    tests = load_tests(data_dir)
    ids = tests.get("ids", [])
    runs = load_all_runs(data_dir)
    summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "tests": [],
    }
    for idx in range(len(ids)):
        cells: Dict[str, Dict[str, Any]] = {}
        for run in runs:
            if run.get("infra"):
                continue
            p = run.get("p", "")
            r = run.get("r", "")
            key = f"{p}|{r}"
            outcomes = run.get("o", "")
            if idx >= len(outcomes):
                continue
            oc = outcomes[idx]
            if oc == OUTCOME_ABSENT:
                continue
            cell = cells.setdefault(
                key,
                {
                    "p": 0,
                    "f": 0,
                    "s": 0,
                    "e": 0,
                    "x": 0,
                    "h": "",
                    "rids": [],
                },
            )
            if oc == OUTCOME_PASS:
                cell["p"] += 1
            elif oc == OUTCOME_FAIL:
                cell["f"] += 1
            elif oc == OUTCOME_SKIP:
                cell["s"] += 1
            elif oc == OUTCOME_ERROR:
                cell["e"] += 1
            elif oc == OUTCOME_XFAIL:
                cell["x"] += 1
            cell["h"] += oc
            cell["rids"].append(run.get("id", 0))
        for cell in cells.values():
            p = cell["p"]
            f = cell["f"]
            e = cell["e"]
            denom = p + f + e
            cell["rate"] = round(p * 100.0 / denom, 1) if denom else 0.0
            cell["flips"] = _count_flips(cell["h"])
            cell["n"] = len(cell["h"])
            cell["h"] = cell["h"][-30:]
            cell["rids"] = cell["rids"][-30:]
        summary["tests"].append({"i": idx, "c": cells})
    save_json(data_dir / "summary.json", summary)


def _count_flips(history: str) -> int:
    flips = 0
    for i in range(1, len(history)):
        prev = history[i - 1]
        curr = history[i]
        if {prev, curr} == {OUTCOME_PASS, OUTCOME_FAIL}:
            flips += 1
    return flips


def cmd_summarize(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    cmd_summarize_impl(data_dir)
    print("summary.json regenerated")
    return 0


# === Rollup command ======================================================


def cmd_rollup(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    retention_days = args.retention_days
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=retention_days
    )
    runs_dir = data_dir / "runs"
    archive_dir = data_dir / "archive"
    if not runs_dir.exists():
        print("No runs directory found")
        return 0
    for shard_path in sorted(runs_dir.glob("*.json")):
        shard = load_json(shard_path)
        month = shard.get("month", shard_path.stem)
        first_ts = ""
        for run in shard.get("runs", []):
            ts = run.get("t", "")
            if ts and (not first_ts or ts < first_ts):
                first_ts = ts
        if not first_ts:
            continue
        try:
            shard_date = datetime.datetime.strptime(
                first_ts, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        if shard_date >= cutoff:
            continue
        archive_path = archive_dir / f"{month}.json"
        archive = _build_archive(shard)
        save_json(archive_path, archive)
        validate_archive(archive_path, shard)
        shard_path.unlink()
        print(f"Archived {month}")
    all_runs = load_all_runs(data_dir)
    state = load_state(data_dir)
    update_index(data_dir, all_runs, state)
    cmd_summarize_impl(data_dir)
    validate(data_dir)
    return 0


def _build_archive(
    shard: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a compact archive from a detail shard."""
    return {
        "schema_version": SCHEMA_VERSION,
        "month": shard.get("month", ""),
        "runs": [
            {
                "id": r.get("id"),
                "wf": r.get("wf"),
                "p": r.get("p"),
                "r": r.get("r"),
                "concl": r.get("concl"),
                "infra": r.get("infra"),
                "n": r.get("n"),
                "t": r.get("t"),
            }
            for r in shard.get("runs", [])
        ],
    }


def validate_archive(archive_path: Path, shard: Dict[str, Any]) -> None:
    archive = load_json(archive_path)
    arch_runs = archive.get("runs", [])
    shard_runs = shard.get("runs", [])
    if len(arch_runs) != len(shard_runs):
        raise ValueError(
            f"archive {archive_path} run count mismatch: "
            f"{len(arch_runs)} vs {len(shard_runs)}"
        )


# === Validate command ====================================================


def validate(data_dir: Path) -> None:
    """Check storage invariants; raise on corruption."""
    tests = load_tests(data_dir)
    ids = tests.get("ids", [])
    if len(ids) != len(set(ids)):
        raise ValueError("tests.json has duplicate ids")
    index = load_json(data_dir / "index.json")
    all_runs = load_all_runs(data_dir)
    run_ids: set = set()
    for run in all_runs:
        rid = run.get("id")
        if rid in run_ids:
            raise ValueError(f"duplicate run id: {rid}")
        run_ids.add(rid)
        outcomes = run.get("o", "")
        for ch in outcomes:
            if ch not in ALL_OUTCOMES:
                raise ValueError(f"unknown outcome '{ch}' in run {rid}")
        if len(outcomes) > len(ids):
            raise ValueError(f"run {rid} outcome string longer than ids")
    for month in index.get("months", []):
        if not (data_dir / "runs" / f"{month}.json").exists():
            raise ValueError(f"month {month} in index but not on disk")
    archive_dir = data_dir / "archive"
    if archive_dir.exists():
        for arch in archive_dir.glob("*.json"):
            if arch.stem in index.get("months", []):
                raise ValueError(f"archived month {arch.stem} still in runs/")
    summary = load_json(data_dir / "summary.json")
    if summary and summary.get("tests"):
        if len(summary["tests"]) != len(ids):
            raise ValueError("summary.json test count != tests.json")


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        validate(Path(args.data_dir))
        print("validation passed")
        return 0
    except ValueError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1


# === Ingest command ======================================================


def cmd_ingest(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    junit_path = Path(args.junit)
    if not junit_path.exists():
        print(f"junit file not found: {junit_path}", file=sys.stderr)
        return 1
    xml_bytes = junit_path.read_bytes()
    parsed = parse_junit(xml_bytes)
    install_source = ""
    if args.meta:
        meta_path = Path(args.meta)
        if meta_path.exists():
            meta = load_json(meta_path)
            install_source = meta.get("install_source", "")
    nodeids = [pt.nodeid for pt in parsed]
    index_map = intern_nodeids(data_dir, nodeids)
    tests = load_tests(data_dir)
    total_ids = len(tests.get("ids", []))
    outcome_str = build_outcome_string(parsed, index_map, total_ids)
    record = RunRecord(
        run_id=args.run_id,
        workflow=args.workflow,
        platform=args.platform,
        release=args.release,
        version=args.version,
        image_type=args.image_type,
        install_source=install_source,
        event=args.event,
        timestamp=args.timestamp or utc_now_iso(),
        sha=args.sha,
        conclusion=args.conclusion,
        attempt=args.attempt,
        test_count=len(parsed),
        infra=len(parsed) == 0,
        outcomes=outcome_str,
    )
    append_run(data_dir, record)
    state = load_state(data_dir)
    if record.run_id not in state.get("processed", []):
        state.setdefault("processed", []).append(record.run_id)
    save_state(data_dir, state)
    all_runs = load_all_runs(data_dir)
    update_index(data_dir, all_runs, state)
    cmd_summarize_impl(data_dir)
    validate(data_dir)
    print(
        f"Ingested {len(parsed)} tests from {junit_path}"
        f" (run_id={record.run_id})"
    )
    return 0


# === check-nodeid-mapping command ========================================


def cmd_check_nodeid_mapping(args: argparse.Namespace) -> int:
    """Walk the real test tree and assert node-id round-trip."""
    import ast

    tests_root = Path(args.tests_dir)
    if not tests_root.exists():
        print(f"tests dir not found: {tests_root}", file=sys.stderr)
        return 1
    failures: List[str] = []
    checked = 0
    for py_file in sorted(tests_root.rglob("test_*.py")):
        rel = py_file.relative_to(tests_root.parent)
        module_path = str(rel).replace("/", ".")[:-3]
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.FunctionDef):
                        if child.name.startswith("test_"):
                            nodeid = (
                                f"{'/'.join(module_path.split('.'))}.py"
                                f"::{node.name}::{child.name}"
                            )
                            names = mangle_test_address(nodeid)
                            classname = ".".join(names[:-1])
                            name = names[-1]
                            reconstructed = reconstruct_nodeid(classname, name)
                            checked += 1
                            if reconstructed != nodeid:
                                failures.append(
                                    f"  {nodeid}\n    -> {reconstructed}"
                                )
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_") and not isinstance(
                    getattr(node, "parent", None), ast.ClassDef
                ):
                    nodeid = (
                        f"{'/'.join(module_path.split('.'))}.py"
                        f"::{node.name}"
                    )
                    names = mangle_test_address(nodeid)
                    classname = ".".join(names[:-1])
                    name = names[-1]
                    reconstructed = reconstruct_nodeid(classname, name)
                    checked += 1
                    if reconstructed != nodeid:
                        failures.append(f"  {nodeid}\n    -> {reconstructed}")
    if failures:
        print(
            f"Node-id mapping failures ({len(failures)}/{checked}):",
            file=sys.stderr,
        )
        for f in failures[:20]:
            print(f, file=sys.stderr)
        return 1
    print(f"All {checked} node ids round-trip correctly")
    return 0


# === Serve command =======================================================


def cmd_serve(args: argparse.Namespace) -> int:
    serve_dir = Path(args.serve_dir)
    if not serve_dir.exists():
        print(f"serve dir not found: {serve_dir}", file=sys.stderr)
        return 1
    port = args.port
    os.chdir(str(serve_dir))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"Serving {serve_dir} on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping")
    return 0


# === CLI =================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    p_collect = sub.add_parser(
        "collect", aliases=["aggregate"], help="Fetch and ingest runs"
    )
    p_collect.add_argument("--data-dir", required=True)
    p_collect.add_argument("--owner", default=DEFAULT_OWNER)
    p_collect.add_argument("--repo", default=DEFAULT_REPO)
    p_collect.add_argument("--since-days", type=int, default=2)
    p_collect.add_argument("--workflow-pattern", default="")
    p_collect.add_argument("--include-manual", action="store_true")
    p_collect.add_argument("--dry-run", action="store_true")
    p_collect.set_defaults(func=cmd_collect)

    p_sum = sub.add_parser("summarize", help="Recompute summary.json")
    p_sum.add_argument("--data-dir", required=True)
    p_sum.set_defaults(func=cmd_summarize)

    p_roll = sub.add_parser("rollup", help="Archive old shards")
    p_roll.add_argument("--data-dir", required=True)
    p_roll.add_argument(
        "--retention-days", type=int, default=DETAIL_RETENTION_DAYS
    )
    p_roll.set_defaults(func=cmd_rollup)

    p_val = sub.add_parser(
        "validate", aliases=["verify"], help="Check invariants"
    )
    p_val.add_argument("--data-dir", required=True)
    p_val.set_defaults(func=cmd_validate)

    p_ing = sub.add_parser("ingest", help="Offline ingest one run")
    p_ing.add_argument("--data-dir", required=True)
    p_ing.add_argument("--junit", required=True)
    p_ing.add_argument("--meta", default="")
    p_ing.add_argument("--platform", required=True)
    p_ing.add_argument("--release", required=True)
    p_ing.add_argument("--version", required=True)
    p_ing.add_argument("--image-type", default="generic")
    p_ing.add_argument("--workflow", required=True)
    p_ing.add_argument("--event", default="schedule")
    p_ing.add_argument("--timestamp", default="")
    p_ing.add_argument("--sha", default="")
    p_ing.add_argument("--conclusion", default="success")
    p_ing.add_argument("--run-id", type=int, required=True)
    p_ing.add_argument("--attempt", type=int, default=1)
    p_ing.set_defaults(func=cmd_ingest)

    p_chk = sub.add_parser(
        "check-nodeid-mapping", help="Verify node-id round-trip"
    )
    p_chk.add_argument(
        "--tests-dir",
        default="tests/integration_tests",
    )
    p_chk.set_defaults(func=cmd_check_nodeid_mapping)

    p_serve = sub.add_parser("serve", help="Local preview server")
    p_serve.add_argument("--serve-dir", default=".")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
