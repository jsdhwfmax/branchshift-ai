"""Fingerprint the actual orchestrator source; never include runtime secrets."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import TypedDict

from app.config import Settings


class SourceProvenance(TypedDict):
    orchestrator_revision: str | None
    orchestrator_digest: str
    orchestrator_dirty: bool | None


def source_provenance(app_directory: Path | None = None) -> SourceProvenance:
    directory = app_directory or Path(__file__).resolve().parent
    api_directory = directory.parent
    root = directory.parents[2]
    digest = hashlib.sha256()
    paths = sorted(directory.rglob("*.py")) + [api_directory / "pyproject.toml"]
    for path in paths:
        if path.is_file():
            digest.update(str(path.relative_to(api_directory)).encode("utf-8") + b"\0")
            digest.update(path.read_bytes() + b"\0")
    revision = None
    dirty = None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2, check=True,
        )
        revision = result.stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=2, check=True,
        )
        dirty = bool(status.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "orchestrator_revision": revision,
        "orchestrator_digest": digest.hexdigest(),
        "orchestrator_dirty": dirty,
    }


def runtime_config_digest(settings: Settings) -> str:
    config = {
        "model": settings.nemotron_model,
        "enable_thinking": settings.nemotron_enable_thinking,
        "run_timeout_seconds": settings.run_timeout_seconds,
        "contree_image": settings.contree_image,
        "mode": settings.mode,
    }
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
