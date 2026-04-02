from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlarmView:
    selector: str
    time: str
    enabled: bool
    label: str


@dataclass(frozen=True)
class StageTemperatureView:
    stage: str
    label: str
    value: str


@dataclass(frozen=True)
class DashboardView:
    bed_is_on: bool
    current_temperature: str | None
    alarms: tuple[AlarmView, ...]
    stage_temperatures: tuple[StageTemperatureView, ...]

    @classmethod
    def empty(cls) -> DashboardView:
        return cls(
            bed_is_on=False,
            current_temperature=None,
            alarms=(),
            stage_temperatures=(),
        )
