"""Deterministic PEP 621 dependency migration; repository TOML remains data."""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from typing import Any

import tomlkit
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from tomlkit.items import Array, String

from app.orchestrator.patches import UnsafePatch
from app.orchestrator.preflight import validate_replacement_source

_TARGET = SpecifierSet(">=2,<3")
_PREFIX = re.compile(r"\s*[A-Za-z0-9][A-Za-z0-9._-]*(?:\s*\[[^\]]*\])?\s*")


def migrate_pyproject_pydantic(original: str) -> str:
    """Change only Pydantic specifiers, retaining extras, markers, trivia and metadata."""
    try:
        document = tomlkit.parse(original)
    except tomlkit.exceptions.ParseError as exc:
        raise UnsafePatch(f"Original pyproject.toml is invalid TOML: {exc}") from exc
    project = document.get("project", {})
    if not isinstance(project, MutableMapping):
        raise UnsafePatch("pyproject.toml: project must be a TOML table")
    groups: list[Any] = []
    if "dependencies" in project:
        groups.append(project["dependencies"])
    optional = project.get("optional-dependencies", {})
    if not isinstance(optional, MutableMapping):
        raise UnsafePatch("pyproject.toml: optional-dependencies must be a TOML table")
    groups.extend(optional.values())
    for requirements in groups:
        if not isinstance(requirements, Array):
            raise UnsafePatch("pyproject.toml: dependencies must be arrays of requirement strings")
        for index, item in enumerate(requirements):
            if not isinstance(item, String):
                raise UnsafePatch("pyproject.toml: dependencies must contain requirement strings")
            try:
                requirement = Requirement(str(item))
            except InvalidRequirement as exc:
                raise UnsafePatch(
                    f"pyproject.toml: invalid dependency requirement: {item}"
                ) from exc
            if canonicalize_name(requirement.name) != "pydantic":
                continue
            if requirement.url:
                raise UnsafePatch(
                    "Pydantic direct URL dependencies cannot be migrated as version pins"
                )
            if requirement.specifier == _TARGET:
                continue
            updated = _replace_specifier(str(item))
            parsed = Requirement(updated)
            if (
                parsed.specifier != _TARGET
                or parsed.name != requirement.name
                or parsed.extras != requirement.extras
                or parsed.marker != requirement.marker
            ):
                raise UnsafePatch(
                    "Pydantic requirement update could not preserve extras and markers"
                )
            requirements[index] = String.from_raw(updated, type_=item.type)
    result = tomlkit.dumps(document)
    validate_replacement_source("pyproject.toml", original, result)
    return result


def _replace_specifier(original: str) -> str:
    requirement_part, delimiter, marker = original.partition(";")
    prefix = _PREFIX.match(requirement_part)
    if prefix is None:
        raise UnsafePatch("Pydantic requirement has no supported package name")
    old_specifier = requirement_part[prefix.end():]
    trailing = old_specifier[len(old_specifier.rstrip()):]
    return prefix.group() + ">=2,<3" + trailing + delimiter + marker
