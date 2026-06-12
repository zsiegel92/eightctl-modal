from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from py_eightctl.eightsleep import (
    Alarm,
    EightSleepError,
    EightSleepService,
    EmptyRequest,
    SetAlarmEnabledRequest,
    SetCurrentTemperatureRequest,
    SetPowerRequest,
    SetSmartTemperatureRequest,
    SmartTemperatureStage,
)

from eightctl_web.config import AppSettings
from eightctl_web.models import AlarmView, DashboardView, StageTemperatureView

STEP = 10
MIN_LEVEL = -100
MAX_LEVEL = 100


class DashboardController(Protocol):
    def load_dashboard(self) -> DashboardView: ...

    def set_power(self, *, on: bool) -> None: ...

    def adjust_current_temperature(self, *, delta: int) -> None: ...

    def adjust_stage_temperature(self, *, stage: SmartTemperatureStage, delta: int) -> None: ...

    def set_alarm_enabled(self, *, selector: str, enabled: bool) -> None: ...

    def trigger_vibration_test(self) -> None: ...


class EightSleepController:
    def __init__(
        self,
        settings: AppSettings,
        *,
        commit_hook: Callable[[], None] | None = None,
    ) -> None:
        self._settings = settings
        self._commit_hook = commit_hook

    def load_dashboard(self) -> DashboardView:
        service = self._build_service()
        status = service.get_smart_temperature_status(EmptyRequest())
        alarms = [
            alarm
            for alarm in service.list_alarms(EmptyRequest()).alarms
            if not _is_vibration_test_alarm(alarm)
        ]
        self._commit()

        stage_temperatures: tuple[StageTemperatureView, ...] = ()
        if status.smart is not None:
            stage_temperatures = (
                StageTemperatureView(
                    stage=SmartTemperatureStage.BEDTIME,
                    label="Bedtime",
                    value=_format_level(status.smart.bedtime),
                ),
                StageTemperatureView(
                    stage=SmartTemperatureStage.NIGHT,
                    label="Night",
                    value=_format_level(status.smart.night),
                ),
                StageTemperatureView(
                    stage=SmartTemperatureStage.DAWN,
                    label="Dawn",
                    value=_format_level(status.smart.dawn),
                ),
            )

        return DashboardView(
            bed_is_on=status.is_on,
            current_temperature=_format_level(status.current_level) if status.is_on else None,
            alarms=tuple(_to_alarm_view(alarm) for alarm in alarms),
            stage_temperatures=stage_temperatures,
        )

    def set_power(self, *, on: bool) -> None:
        service = self._build_service()
        service.set_power(SetPowerRequest(on=on))
        self._commit()

    def adjust_current_temperature(self, *, delta: int) -> None:
        service = self._build_service()
        status = service.get_status(EmptyRequest())
        next_level = _clamp_level(status.current_level + delta)
        service.set_current_temperature(SetCurrentTemperatureRequest(level=next_level))
        self._commit()

    def adjust_stage_temperature(self, *, stage: SmartTemperatureStage, delta: int) -> None:
        service = self._build_service()
        status = service.get_smart_temperature_status(EmptyRequest())
        if status.smart is None:
            raise EightSleepError("smart temperature settings are unavailable")

        current_level = {
            SmartTemperatureStage.BEDTIME: status.smart.bedtime,
            SmartTemperatureStage.NIGHT: status.smart.night,
            SmartTemperatureStage.DAWN: status.smart.dawn,
        }[stage]

        service.set_smart_temperature(
            SetSmartTemperatureRequest(stage=stage, level=_clamp_level(current_level + delta))
        )
        self._commit()

    def set_alarm_enabled(self, *, selector: str, enabled: bool) -> None:
        service = self._build_service()
        service.set_alarm_enabled(SetAlarmEnabledRequest(selector=selector, enabled=enabled))
        self._commit()

    def trigger_vibration_test(self) -> None:
        service = self._build_service()
        service.alarm_vibration_test(EmptyRequest())
        self._commit()

    def _build_service(self) -> EightSleepService:
        return EightSleepService(
            config_path=self._settings.py_eightctl_config_path,
            post_token_refresh_hook=self._commit,
        )

    def _commit(self) -> None:
        if self._commit_hook is not None:
            self._commit_hook()


def _to_alarm_view(alarm: Alarm) -> AlarmView:
    return AlarmView(
        selector=alarm.fingerprint,
        time=alarm.time[:5],
        enabled=alarm.enabled,
        label="ON" if alarm.enabled else "OFF",
    )


def _is_vibration_test_alarm(alarm: Alarm) -> bool:
    return bool(getattr(alarm, "is_vibration_test", False)) or (
        getattr(alarm, "vibration_pattern", None) == "TESTDRIVE"
    )


def _format_level(value: int) -> str:
    return str(value // STEP)


def _clamp_level(value: int) -> int:
    return max(MIN_LEVEL, min(MAX_LEVEL, value))
