from __future__ import annotations

import hmac
import time
from dataclasses import dataclass
from hashlib import sha256
from secrets import compare_digest

from fastapi import Request

from eightctl_web.config import AppSettings


class AuthenticationRequiredError(Exception):
    pass


@dataclass(frozen=True)
class SessionCookieManager:
    settings: AppSettings

    def create_value(self, now: int | None = None) -> str:
        issued_at = str(now or int(time.time()))
        signature = self._sign(issued_at)
        return f"{issued_at}.{signature}"

    def is_valid(self, value: str | None, now: int | None = None) -> bool:
        if not value:
            return False

        issued_at, separator, signature = value.partition(".")
        if separator != "." or not issued_at or not signature:
            return False
        if not issued_at.isdigit():
            return False
        if not hmac.compare_digest(signature, self._sign(issued_at)):
            return False

        issued_at_int = int(issued_at)
        current_time = now or int(time.time())
        return current_time - issued_at_int <= self.settings.session_max_age_seconds

    def _sign(self, issued_at: str) -> str:
        return hmac.new(
            self.settings.session_secret,
            issued_at.encode("utf-8"),
            sha256,
        ).hexdigest()


def credentials_match(settings: AppSettings, email: str, password: str) -> bool:
    return compare_digest(email.strip(), settings.py_eightctl_email) and compare_digest(
        password,
        settings.py_eightctl_password,
    )


def require_login(request: Request) -> None:
    auth = request.app.state.session_cookie_manager
    cookie_name = request.app.state.settings.session_cookie_name
    if not auth.is_valid(request.cookies.get(cookie_name)):
        raise AuthenticationRequiredError
