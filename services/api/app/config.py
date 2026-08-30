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


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv("BRANCHSHIFT_MODE", "mock")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./branchshift.db")
    mock_step_delay_seconds: float = _float_env("MOCK_STEP_DELAY_SECONDS", 0.18)
    run_timeout_seconds: int = _int_env("RUN_TIMEOUT_SECONDS", 900)
    max_concurrent_runs: int = _int_env("MAX_CONCURRENT_RUNS", 2)
    nebius_api_key: str = os.getenv("NEBIUS_API_KEY", "")
    nebius_base_url: str = os.getenv(
        "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"
    )
    nemotron_model: str = os.getenv(
        "NEMOTRON_MODEL", "nvidia/Nemotron-3_5-Lightning"
    )
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    contree_api_url: str = os.getenv(
        "CONTREE_API_URL", "https://api.tokenfactory.nebius.com/sandboxes"
    )
    contree_image: str = os.getenv("CONTREE_IMAGE", "python:3.13-slim")

    @property
    def is_mock(self) -> bool:
        return self.mode.lower() != "live"


settings = Settings()
