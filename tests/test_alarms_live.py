"""Opt-in live round trip: EIGHTCTL_LIVE_ALARM_TIME=04:30 pytest tests/test_alarms_live.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from py_eightctl.eightsleep.client import EightSleepClient
from py_eightctl.eightsleep.models import CredentialsInput, RoutinesPayload, StoredConfig
from py_eightctl.eightsleep.service import EightSleepService

from eightctl_web.config import load_settings
from eightctl_web.service import EightSleepController


def test_live_alarm_toggle_changes_only_the_selected_alarm(tmp_path: Path) -> None:
    target = os.environ.get("EIGHTCTL_LIVE_ALARM_TIME")
    if not target:
        pytest.skip("Set EIGHTCTL_LIVE_ALARM_TIME to an off one-off alarm in HH:MM format")

    settings = load_settings()
    credentials = CredentialsInput(
        email=settings.py_eightctl_email, password=settings.py_eightctl_password
    )
    config_path = tmp_path / "eightctl.json"
    EightSleepService(config_path=config_path).save_credentials(credentials)
    controller = EightSleepController(
        settings.model_copy(update={"py_eightctl_config_path": config_path})
    )
    client = EightSleepClient(StoredConfig(email=credentials.email, password=credentials.password))

    def raw_flags() -> dict[str, bool]:
        raw = client._fetch_routines_payload()  # pyright: ignore[reportPrivateUsage]
        alarms = RoutinesPayload.model_validate(raw).settings.one_off_alarms
        flags = {alarm.time[:5]: alarm.enabled for alarm in alarms}
        assert len(flags) == len(alarms), "Live test requires unique one-off alarm times"
        return flags

    dashboard = controller.load_dashboard()
    before = {alarm.time: alarm.enabled for alarm in dashboard.alarms}
    raw_before = raw_flags()
    assert len(before) == len(dashboard.alarms), "Live test requires unique dashboard alarm times"
    assert before.get(target) is raw_before.get(target) is False, "Target must start off"
    selected = next(alarm for alarm in dashboard.alarms if alarm.time == target)

    try:
        controller.set_alarm_enabled(selector=selected.selector, enabled=True)
        assert raw_flags() == {**raw_before, target: True}
        assert {alarm.time: alarm.enabled for alarm in controller.load_dashboard().alarms} == {
            **before,
            target: True,
        }
    finally:
        if raw_flags()[target]:
            updated = next(
                alarm for alarm in controller.load_dashboard().alarms if alarm.time == target
            )
            controller.set_alarm_enabled(selector=updated.selector, enabled=False)
        assert raw_flags() == raw_before
        assert {alarm.time: alarm.enabled for alarm in controller.load_dashboard().alarms} == before
