# This file is part of cloud-init. See LICENSE file for license information.
"""Integration tests for cloudinit.log.security_event_log.

Validates that OWASP-formatted security event entries are written to
/var/log/cloud-init-security.log for:
  - user creation   (USER_CREATED / user_created)
  - password change (AUTHN_PASSWORD_CHANGE / authn_password_change)
  - system reboot   (SYS_RESTART / sys_restart)
"""
import json
import time

import pytest

from tests.integration_tests.instances import IntegrationInstance
from tests.integration_tests.integration_settings import PLATFORM
from tests.integration_tests.releases import IS_UBUNTU

SECURITY_LOG_FILE = "/var/log/cloud-init-security.log"

# ---------------------------------------------------------------------------
# Cloud-config snippets
# ---------------------------------------------------------------------------

USER_CREATION_USER_DATA = """\
#cloud-config
users:
  - name: sectest1
    gecos: Security Test User 1
    lock_passwd: true
  - name: sectest2
    gecos: Security Test User 2
    lock_passwd: true
"""

PASSWORD_CHANGE_USER_DATA = """\
#cloud-config
users:
  - name: pwuser
    gecos: Password Change Test User
    lock_passwd: false
    hashed_passwd: $6$j212wezy$7H/1LT4f9/N3wpgNunhsIqtMj62OKiS3nyNwuizouQc3u7MbYCarYeAHWYPYb2FT.lbioDm2RrkJPb9BZMN1O/
"""  # noqa: E501

REBOOT_USER_DATA = """\
#cloud-config
power_state:
  delay: now
  mode: reboot
  message: cloud-init-security-test-reboot
  timeout: 30
  condition: true
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_security_log(log_content: str) -> list:
    """Return a list of dicts, one per non-empty JSON line in *log_content*."""
    events = []
    for line in log_content.splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _filter_events(events: list, event_prefix: str) -> list:
    """Return events whose ``event`` field starts with *event_prefix*."""
    return [e for e in events if e.get("event", "").startswith(event_prefix)]


def _assert_owasp_fields(event: dict) -> None:
    """Assert all mandatory OWASP envelope fields are present and valid."""
    assert (
        event.get("appid") == "canonical.cloud_init"
    ), f"appid mismatch in event: {event}"
    assert "datetime" in event, f"Missing 'datetime' in event: {event}"
    # ISO 8601 requires a 'T' separator and a UTC offset
    assert (
        "T" in event["datetime"]
    ), f"datetime '{event['datetime']}' not ISO 8601"
    assert (
        "+" in event["datetime"] or "Z" in event["datetime"]
    ), f"datetime '{event['datetime']}' has no timezone offset"
    assert "hostname" in event, f"Missing 'hostname' in event: {event}"
    assert event.get("level") in (
        "INFO",
        "WARN",
        "CRITICAL",
    ), f"Unexpected level '{event.get('level')}' in event: {event}"


def _detect_reboot(instance: IntegrationInstance) -> None:
    """Block until cloud-init.log records at least two 'init-local' runs."""
    instance.instance.wait()
    for _ in range(600):
        try:
            log = instance.read_from_file("/var/log/cloud-init.log")
            if log.count("running 'init-local'") >= 2:
                return
        except Exception:
            pass
        time.sleep(1)
    raise AssertionError("Instance did not reboot within the expected window")


# ---------------------------------------------------------------------------
# Test: user creation
# ---------------------------------------------------------------------------


@pytest.mark.ci
@pytest.mark.user_data(USER_CREATION_USER_DATA)
def test_user_created_security_events(client: IntegrationInstance):
    """A user_created event is written for each new user created by cloud-init.

    The decorator ``sec_log_user_created`` on ``Distro.create_user`` emits a
    WARN-level JSON entry per successfully created user.
    """
    log_content = client.read_from_file(SECURITY_LOG_FILE)
    events = _parse_security_log(log_content)
    user_events = _filter_events(events, "user_created:")

    # Collect the usernames referenced in the log
    logged_users = {
        e["event"].split(":", 1)[1].split(",", 1)[-1] for e in user_events
    }

    assert "sectest1" in logged_users, (
        f"No user_created entry for 'sectest1'. "
        f"user_created events found: {user_events}"
    )
    assert "sectest2" in logged_users, (
        f"No user_created entry for 'sectest2'. "
        f"user_created events found: {user_events}"
    )

    # Validate every sectest* entry in detail
    for username in ("sectest1", "sectest2"):
        matching = [
            e
            for e in user_events
            if e["event"] == f"user_created:cloud-init,{username}"
        ]
        assert matching, f"Exact user_created event not found for '{username}'"
        event = matching[0]
        _assert_owasp_fields(event)
        assert event["level"] == "WARN", (
            f"user_created event for '{username}' should be WARN, "
            f"got '{event['level']}'"
        )
        assert (
            event["description"] == f"User '{username}' was created"
        ), f"Unexpected description in event: {event}"


# ---------------------------------------------------------------------------
# Test: password change
# ---------------------------------------------------------------------------


@pytest.mark.ci
@pytest.mark.user_data(PASSWORD_CHANGE_USER_DATA)
def test_password_change_security_events(client: IntegrationInstance):
    """An authn_password_change event is written when Distro.set_passwd runs.

    The decorator ``sec_log_password_changed`` on ``Distro.set_passwd`` emits
    an INFO-level JSON entry whenever a user password is set via
    ``create_user``  (triggered by ``plain_text_passwd`` or ``hashed_passwd``
    in user-data).
    """
    log_content = client.read_from_file(SECURITY_LOG_FILE)
    events = _parse_security_log(log_content)
    pw_events = _filter_events(events, "authn_password_change:")

    assert pw_events, (
        "Expected at least one authn_password_change event. "
        f"Security log:\n{log_content}"
    )

    event = pw_events[0]
    _assert_owasp_fields(event)
    assert (
        event["level"] == "INFO"
    ), f"authn_password_change should be INFO, got '{event['level']}'"
    # The event string must start with the cloud-init actor prefix
    assert event["event"].startswith(
        "authn_password_change:cloud-init,"
    ), f"Unexpected event string format: {event['event']}"


# ---------------------------------------------------------------------------
# Test: system reboot
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not IS_UBUNTU, reason="Only tested on Ubuntu")
@pytest.mark.skipif(
    PLATFORM != "lxd_container",
    reason="Reboot detection is most reliable on lxd_container",
)
def test_reboot_security_event(session_cloud):
    """A sys_restart event is written when power_state triggers a reboot.

    The decorator ``sec_log_system_shutdown`` on ``Distro.shutdown_command``
    emits an INFO-level JSON entry before the shutdown command runs.
    """
    with session_cloud.launch(
        user_data=REBOOT_USER_DATA,
        wait=False,
    ) as instance:
        _detect_reboot(instance)
        log_content = instance.read_from_file(SECURITY_LOG_FILE)

    events = _parse_security_log(log_content)
    restart_events = _filter_events(events, "sys_restart:")

    assert restart_events, (
        "Expected at least one sys_restart event in security log. "
        f"Log content:\n{log_content}"
    )

    event = restart_events[0]
    _assert_owasp_fields(event)
    assert (
        event["event"] == "sys_restart:cloud-init"
    ), f"Unexpected event string: {event['event']}"
    assert (
        event["level"] == "INFO"
    ), f"sys_restart event should be INFO, got '{event['level']}'"
    assert (
        event["description"] == "System restart initiated"
    ), f"Unexpected description: {event['description']}"
