from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _limit_env(name: str, default: int) -> int:
    """Admission settings must fail closed on a mistyped deployment value."""
    value = int(os.getenv(name, str(default)))
    if value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv("BRANCHSHIFT_MODE", "mock")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./branchshift.db")
    mock_step_delay_seconds: float = _float_env("MOCK_STEP_DELAY_SECONDS", 0.18)
    run_timeout_seconds: int = _int_env("RUN_TIMEOUT_SECONDS", 900)
    max_concurrent_runs: int = _int_env("MAX_CONCURRENT_RUNS", 2)
    http_max_body_bytes: int = _limit_env("HTTP_MAX_BODY_BYTES", 8192)
    http_daily_run_limit: int = _limit_env("HTTP_DAILY_RUN_LIMIT", 5)
    http_lifetime_run_limit: int = _limit_env("HTTP_LIFETIME_RUN_LIMIT", 20)
    http_max_pending_runs: int = _limit_env("HTTP_MAX_PENDING_RUNS", 2)
    http_client_daily_run_limit: int = _limit_env("HTTP_CLIENT_DAILY_RUN_LIMIT", 2)
    http_client_max_outstanding_runs: int = _limit_env("HTTP_CLIENT_MAX_OUTSTANDING_RUNS", 1)
    nebius_api_key: str = os.getenv("NEBIUS_API_KEY", "")
    nebius_project_id: str = os.getenv("NEBIUS_PROJECT_ID", "")
    nebius_base_url: str = os.getenv(
        "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"
    )
    nemotron_model: str = os.getenv(
        "NEMOTRON_MODEL", "nvidia/Nemotron-3_5-Lightning"
    )
    nemotron_enable_thinking: bool = os.getenv(
        "NEMOTRON_ENABLE_THINKING", "false"
    ).lower() == "true"
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    contree_api_url: str = os.getenv(
        "CONTREE_API_URL", "https://api.tokenfactory.nebius.com/sandboxes"
    )
    contree_image: str = os.getenv("CONTREE_IMAGE", "python:3.13-slim")

    def __post_init__(self) -> None:
        for name in (
            "http_daily_run_limit", "http_lifetime_run_limit", "http_max_pending_runs",
            "http_client_daily_run_limit", "http_client_max_outstanding_runs",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.http_max_body_bytes < 1 or self.max_concurrent_runs < 1:
            raise ValueError("HTTP_MAX_BODY_BYTES and MAX_CONCURRENT_RUNS must be positive")

    @property
    def is_mock(self) -> bool:
        return self.mode.lower() != "live"


settings = Settings()
