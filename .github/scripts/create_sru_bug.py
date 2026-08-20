#!/usr/bin/env python3
"""Create a Launchpad cloud-init SRU bug from the latest GitHub release.

Usable both from a GitHub Actions workflow (see .github/actions/
create-sru-bug/action.yml and .github/workflows/create-sru-bug.yml) and
directly from the command line. By default it performs a safe dry run:
it prints the bug title and description without creating anything. Pass
--create (or set CREATE=true) to actually file the bug against the
ubuntu/cloud-init source package on Launchpad.

Authentication: set LP_CREDENTIALS to a serialized launchpadlib
credentials string. Generate one locally with::

    from launchpadlib.credentials import Credentials
    from launchpadlib.launchpad import Launchpad
    creds = Launchpad.login_with(
        "ci-sru-bug-filer", "production",
        credentials_file="/tmp/lpcreds",
    )
    raw = open("/tmp/lpcreds").read()  # store `raw` as the LP_CREDENTIALS
                                       # GitHub repository secret

The script loads it back with Credentials.from_string(LP_CREDENTIALS).

Environment variables (all optional unless filing):
    CREATE            truthy -> file the bug (default: dry run)
    VERSION           override the version detected from the latest release
    GITHUB_TOKEN      optional; raises GitHub API rate limits
    LP_CREDENTIALS    serialized launchpadlib credentials (required to file)
    GITHUB_OUTPUT     when set, action outputs are written there
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/canonical/cloud-init/releases/latest"
)
SRU_DOC_URL = (
    "https://documentation.ubuntu.com/sru/en/latest/"
    "reference/exception-Cloudinit-Updates"
)
DISTRIBUTION = "ubuntu"
SOURCE_PACKAGE = "cloud-init"
TEMPLATE_FILE = Path(__file__).resolve().parent / "sru_template.txt"
IMPACT_TODO = "*** <TODO-PRIOR-TO-PROPOSED>: Create list with LP: # included>"


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_template():
    return TEMPLATE_FILE.read_text(encoding="utf-8")


def fetch_latest_release(github_token):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "cloud-init-sru-bug-filer",
    }
    if github_token:
        headers["Authorization"] = "Bearer " + github_token
    request = urllib.request.Request(GITHUB_RELEASES_URL, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            "GitHub API request failed: HTTP %d %s" % (exc.code, exc.reason)
        ) from exc


def parse_highlights(body):
    lines = body.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().lower().startswith("## highlights"):
            start = index + 1
            break
    if start is None:
        return None
    collected = []
    for line in lines[start:]:
        if line.strip().startswith("## "):
            break
        collected.append(line)
    while collected and not collected[0].strip():
        collected.pop(0)
    while collected and not collected[-1].strip():
        collected.pop()
    return "\n".join(collected) if collected else None


def build_title(version):
    return "sru cloud-init version " + version


def build_description(highlights, release_url):
    highlights_block = highlights if highlights else IMPACT_TODO
    return load_template().format(
        highlights=highlights_block,
        release_url=release_url,
        sru_doc_url=SRU_DOC_URL,
    )


def login_launchpad(credentials_string):
    from launchpadlib.credentials import Credentials
    from launchpadlib.launchpad import Launchpad

    credentials = Credentials.from_string(credentials_string)
    return Launchpad(
        credentials,
        None,
        None,
        service_root="production",
        version="1.0",
    )


def file_bug(launchpad, title, description):
    distribution = launchpad.distributions[DISTRIBUTION]
    source_package = distribution.getSourcePackage(name=SOURCE_PACKAGE)
    return launchpad.bugs.createBug(
        title=title,
        description=description,
        target=source_package,
    )


def write_step_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path or value is None:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("%s=%s\n" % (name, value))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Launchpad cloud-init SRU bug.",
    )
    parser.add_argument(
        "--create",
        nargs="?",
        const="true",
        default=os.environ.get("CREATE", "false"),
        help="truthy value to file the bug on Launchpad (default: dry run)",
    )
    parser.add_argument(
        "--version",
        default=os.environ.get("VERSION"),
        help="override the version from the latest release",
    )
    parser.add_argument(
        "--github-token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token to raise API rate limits",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    create = truthy(args.create)

    release = fetch_latest_release(args.github_token)
    version = args.version or release.get("tag_name")
    if not version:
        raise RuntimeError("could not determine release version")
    release_url = release.get("html_url") or (
        "https://github.com/canonical/cloud-init/releases/tag/" + version
    )
    highlights = parse_highlights(release.get("body") or "")

    title = build_title(version)
    description = build_description(highlights, release_url)

    print("Title: " + title)
    print("Version: " + version)
    print("Release: " + release_url)
    print("Description:")
    print(description)

    write_step_output("version", version)
    write_step_output("title", title)
    write_step_output("release-url", release_url)

    if not create:
        print("\n[dry-run] not filing the bug. Pass --create to file it.")
        return 0

    credentials = os.environ.get("LP_CREDENTIALS")
    if not credentials:
        raise RuntimeError("LP_CREDENTIALS is required to file a bug")

    launchpad = login_launchpad(credentials)
    bug = file_bug(launchpad, title, description)
    bug_url = bug.web_link
    bug_id = str(bug.id)
    print("\n[created] Launchpad bug: " + bug_url)
    write_step_output("bug-url", bug_url)
    write_step_output("bug-id", bug_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print("error: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
