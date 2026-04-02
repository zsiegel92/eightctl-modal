from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    py_eightctl_email: str = Field(alias="PY_EIGHTCTL_EMAIL")
    py_eightctl_password: str = Field(alias="PY_EIGHTCTL_PASSWORD")
    py_eightctl_config_path: Path = Field(
        default=Path("/data/py-eightctl-config.json"),
        alias="PY_EIGHTCTL_CONFIG_PATH",
    )
    template_dir: Path = Field(
        default=Path(__file__).resolve().parent / "templates",
        alias="EIGHTCTL_WEB_TEMPLATES_DIR",
    )
    session_cookie_name: str = Field(
        default="eightctl_session",
        alias="EIGHTCTL_WEB_SESSION_COOKIE",
    )
    session_max_age_seconds: int = Field(
        default=60 * 60 * 24 * 30,
        alias="EIGHTCTL_WEB_SESSION_MAX_AGE_SECONDS",
    )

    @property
    def session_secret(self) -> bytes:
        material = (
            f"{self.py_eightctl_email}\0{self.py_eightctl_password}\0eightctl-web-session"
        ).encode()
        return sha256(material).digest()


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    return AppSettings()  # pyright: ignore[reportCallIssue]
