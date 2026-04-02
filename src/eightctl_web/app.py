from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from py_eightctl.eightsleep import EightSleepError, SmartTemperatureStage

from eightctl_web.auth import (
    AuthenticationRequiredError,
    SessionCookieManager,
    credentials_match,
    require_login,
)
from eightctl_web.config import AppSettings, load_settings
from eightctl_web.models import DashboardView
from eightctl_web.service import DashboardController, EightSleepController


def create_app(
    *,
    settings: AppSettings | None = None,
    controller: DashboardController | None = None,
    commit_hook: Callable[[], None] | None = None,
) -> FastAPI:
    app_settings = settings or load_settings()
    dashboard_controller = controller or EightSleepController(app_settings, commit_hook=commit_hook)
    templates = Jinja2Templates(directory=str(app_settings.template_dir))

    app = FastAPI(name="eightctl-web")
    app.state.settings = app_settings
    app.state.session_cookie_manager = SessionCookieManager(app_settings)

    def render_login(
        request: Request,
        *,
        error: str | None = None,
        status_code: int = status.HTTP_200_OK,
    ):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": error},
            status_code=status_code,
        )

    def render_dashboard(
        request: Request,
        *,
        error: str | None = None,
        status_code: int = status.HTTP_200_OK,
    ):
        try:
            dashboard = dashboard_controller.load_dashboard()
        except EightSleepError as exc:
            dashboard = DashboardView.empty()
            error = error or str(exc)

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"dashboard": dashboard, "error": error},
            status_code=status_code,
        )

    @app.exception_handler(AuthenticationRequiredError)
    def handle_authentication_required(request: Request, _: AuthenticationRequiredError):
        return render_login(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    @app.get("/login")
    def login_page(request: Request):
        if app.state.session_cookie_manager.is_valid(
            request.cookies.get(app_settings.session_cookie_name)
        ):
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        return render_login(request)

    @app.post("/login")
    def login(
        request: Request,
        email: Annotated[str, Form()],
        password: Annotated[str, Form()],
    ):
        if not credentials_match(app_settings, email, password):
            return render_login(
                request,
                error="Incorrect email or password.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=app_settings.session_cookie_name,
            value=app.state.session_cookie_manager.create_value(),
            httponly=True,
            max_age=app_settings.session_max_age_seconds,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
        return response

    @app.get("/")
    def dashboard(
        request: Request,
        _: None = Depends(require_login),
    ):
        return render_dashboard(request)

    @app.post("/bed/power")
    def set_bed_power(
        request: Request,
        on: Annotated[bool, Form()],
        _: None = Depends(require_login),
    ):
        try:
            dashboard_controller.set_power(on=on)
        except EightSleepError as exc:
            return render_dashboard(
                request,
                error=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/bed/current-temperature")
    def adjust_current_temperature(
        request: Request,
        delta: Annotated[int, Form()],
        _: None = Depends(require_login),
    ):
        try:
            dashboard_controller.adjust_current_temperature(delta=delta)
        except EightSleepError as exc:
            return render_dashboard(
                request,
                error=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/bed/stage-temperature")
    def adjust_stage_temperature(
        request: Request,
        stage: Annotated[SmartTemperatureStage, Form()],
        delta: Annotated[int, Form()],
        _: None = Depends(require_login),
    ):
        try:
            dashboard_controller.adjust_stage_temperature(stage=stage, delta=delta)
        except EightSleepError as exc:
            return render_dashboard(
                request,
                error=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/alarms/toggle")
    def toggle_alarm(
        request: Request,
        selector: Annotated[str, Form()],
        enabled: Annotated[bool, Form()],
        _: None = Depends(require_login),
    ):
        try:
            dashboard_controller.set_alarm_enabled(selector=selector, enabled=enabled)
        except EightSleepError as exc:
            return render_dashboard(
                request,
                error=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/alarms/vibration-test")
    def vibration_test(
        request: Request,
        _: None = Depends(require_login),
    ):
        try:
            dashboard_controller.trigger_vibration_test()
        except EightSleepError as exc:
            return render_dashboard(
                request,
                error=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return app
