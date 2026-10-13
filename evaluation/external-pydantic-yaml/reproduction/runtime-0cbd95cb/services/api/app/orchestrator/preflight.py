"""Parse candidate source as data before any sandbox execution."""

from __future__ import annotations

import ast
import copy
import importlib
import re
import sys
from pathlib import PurePosixPath
from typing import Any, cast

from app.orchestrator.patches import UnsafePatch

_toml = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")
_PYDANTIC_REQUIREMENT = re.compile(r"^pydantic(?:\[[^\]]+\])?(?:\s*[<>=!~@; ]|$)", re.I)


def validate_replacement_source(path: str, original: str, content: str) -> None:
    suffix = PurePosixPath(path).suffix
    if suffix == ".py":
        try:
            ast.parse(content, filename=path)
        except SyntaxError as exc:
            line = (exc.text or "").strip()[:180]
            raise UnsafePatch(
                f"{path}:{exc.lineno}: invalid Python: {exc.msg}; source line: {line}"
            ) from exc
    elif suffix == ".toml":
        try:
            parsed = cast(dict[str, Any], _toml.loads(content))
        except _toml.TOMLDecodeError as exc:
            raise UnsafePatch(
                f"{path}: invalid TOML: {exc}. Preserve quotes around strings and brackets "
                "around arrays; copy unchanged original lines exactly."
            ) from exc
        if PurePosixPath(path).name == "pyproject.toml":
            baseline = cast(dict[str, Any], _toml.loads(original))
            if _manifest_contract(baseline) != _manifest_contract(parsed):
                raise UnsafePatch(
                    f"{path}: only Pydantic dependency requirement entries may change. "
                    "Preserve build-system, project metadata, other dependencies, package "
                    "discovery, and pytest configuration exactly."
                )


def _manifest_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(manifest)
    project = result.get("project", {})
    if not isinstance(project, dict):
        raise UnsafePatch("pyproject.toml: project must remain a TOML table")
    if "dependencies" in project:
        project["dependencies"] = _requirements_contract(project["dependencies"])
    optional = project.get("optional-dependencies", {})
    if not isinstance(optional, dict):
        raise UnsafePatch("pyproject.toml: optional-dependencies must remain a TOML table")
    for group, requirements in optional.items():
        optional[group] = _requirements_contract(requirements)
    return result


def _requirements_contract(requirements: Any) -> list[str]:
    if not isinstance(requirements, list) or any(
        not isinstance(item, str) for item in requirements
    ):
        raise UnsafePatch("pyproject.toml: dependencies must remain an array of quoted strings")
    return [
        "<pydantic-migration-requirement>" if _PYDANTIC_REQUIREMENT.match(item) else item
        for item in requirements
    ]
