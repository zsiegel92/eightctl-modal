from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from py_eightctl.eightsleep import EmptyRequest, SmartTemperatureStage

from eightctl_web.app import create_app
from eightctl_web.config import AppSettings
from eightctl_web.models import AlarmView, DashboardView, StageTemperatureView
from eightctl_web.service import EightSleepController


@dataclass
class FakeController:
    dashboard: DashboardView = field(
        default_factory=lambda: DashboardView(
            bed_is_on=True,
            current_temperature="-5",
            alarms=(
                AlarmView(selector="alarm-1", time="06:30", enabled=True, label="ON"),
                AlarmView(selector="alarm-2", time="07:15", enabled=False, label="OFF"),
            ),
            stage_temperatures=(
                StageTemperatureView(
                    stage=SmartTemperatureStage.BEDTIME,
                    label="Bedtime",
                    value="-4",
                ),
                StageTemperatureView(
                    stage=SmartTemperatureStage.NIGHT,
                    label="Night",
                    value="-5",
                ),
                StageTemperatureView(
                    stage=SmartTemperatureStage.DAWN,
                    label="Dawn",
                    value="-3",
                ),
            ),
        )
    )
    power_calls: list[bool] = field(default_factory=lambda: cast(list[bool], []))
    current_temperature_calls: list[int] = field(default_factory=lambda: cast(list[int], []))
    stage_temperature_calls: list[tuple[SmartTemperatureStage, int]] = field(
        default_factory=lambda: cast(list[tuple[SmartTemperatureStage, int]], [])
    )
    alarm_calls: list[tuple[str, bool]] = field(
        default_factory=lambda: cast(list[tuple[str, bool]], [])
    )
    vibration_test_calls: int = 0

    def load_dashboard(self) -> DashboardView:
        return self.dashboard

    def set_power(self, *, on: bool) -> None:
        self.power_calls.append(on)

    def adjust_current_temperature(self, *, delta: int) -> None:
        self.current_temperature_calls.append(delta)

    def adjust_stage_temperature(self, *, stage: SmartTemperatureStage, delta: int) -> None:
        self.stage_temperature_calls.append((stage, delta))

    def set_alarm_enabled(self, *, selector: str, enabled: bool) -> None:
        self.alarm_calls.append((selector, enabled))

    def trigger_vibration_test(self) -> None:
        self.vibration_test_calls += 1


def build_settings() -> AppSettings:
    return AppSettings(
        PY_EIGHTCTL_EMAIL="user@example.com",
        PY_EIGHTCTL_PASSWORD="secret",
        EIGHTCTL_WEB_TEMPLATES_DIR=Path("src/eightctl_web/templates"),
    )


def test_login_page_is_served_for_unauthenticated_requests() -> None:
    client = TestClient(create_app(settings=build_settings(), controller=FakeController()))

    response = client.get("/")

    assert response.status_code == 401
    assert "Sign in with the deploy account." in response.text


def test_login_sets_cookie_and_serves_dashboard() -> None:
    client = TestClient(create_app(settings=build_settings(), controller=FakeController()))

    login_response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "secret"},
        follow_redirects=False,
    )

    assert login_response.status_code == 303
    assert "eightctl_session=" in login_response.headers["set-cookie"]
    cookie_value = login_response.cookies.get("eightctl_session")
    assert cookie_value is not None
    client.cookies.set(build_settings().session_cookie_name, cookie_value)

    dashboard_response = client.get("/")

    assert dashboard_response.status_code == 200
    assert "06:30" in dashboard_response.text
    assert "Bedtime" in dashboard_response.text


def test_protected_actions_require_valid_login_cookie() -> None:
    controller = FakeController()
    client = TestClient(create_app(settings=build_settings(), controller=controller))

    login_response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "secret"},
        follow_redirects=False,
    )
    cookie_value = login_response.cookies.get("eightctl_session")
    assert cookie_value is not None
    client.cookies.set(build_settings().session_cookie_name, cookie_value)

    response = client.post(
        "/alarms/toggle",
        data={"selector": "alarm-1", "enabled": "false"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert controller.alarm_calls == [("alarm-1", False)]


def test_vibration_test_triggers_controller_action() -> None:
    controller = FakeController()
    client = TestClient(create_app(settings=build_settings(), controller=controller))

    login_response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "secret"},
        follow_redirects=False,
    )
    cookie_value = login_response.cookies.get("eightctl_session")
    assert cookie_value is not None
    client.cookies.set(build_settings().session_cookie_name, cookie_value)

    response = client.post("/alarms/vibration-test", follow_redirects=False)

    assert response.status_code == 303
    assert controller.vibration_test_calls == 1


def test_vibration_test_alarm_is_filtered_from_dashboard() -> None:
    class FakeService:
        def get_smart_temperature_status(self, request: EmptyRequest) -> FakeSmartStatus:
            del request
            return FakeSmartStatus()

        def list_alarms(self, request: EmptyRequest) -> Any:
            del request
            return type(
                "FakeAlarmList",
                (),
                {
                    "alarms": [
                        type(
                            "FakeAlarm",
                            (),
                            {
                                "fingerprint": "vibe-fingerprint",
                                "time": "12:34:56",
                                "enabled": True,
                                "is_vibration_test": True,
                                "vibration_pattern": "TESTDRIVE",
                            },
                        )(),
                        type(
                            "FakeAlarm",
                            (),
                            {
                                "fingerprint": "real-fingerprint",
                                "time": "06:30:00",
                                "enabled": True,
                                "is_vibration_test": False,
                                "vibration_pattern": "REGULAR",
                            },
                        )(),
                    ]
                },
            )()

    class FakeSmartSettings:
        bedtime = -40
        night = -50
        dawn = -30

    class FakeCurrentState:
        type = "smart"

    class FakeSmartStatus:
        is_on = True
        current_level = -50
        smart = FakeSmartSettings()
        current_state = FakeCurrentState()

    class FakeEightSleepController(EightSleepController):
        def _build_service(self) -> Any:
            return FakeService()

        def _commit(self) -> None:
            return None

    controller = FakeEightSleepController(build_settings())

    dashboard = controller.load_dashboard()

    assert len(dashboard.alarms) == 1
    assert dashboard.alarms[0].time == "06:30"
