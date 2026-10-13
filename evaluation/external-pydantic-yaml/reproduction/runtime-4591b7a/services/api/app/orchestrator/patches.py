from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.orchestrator.planner import is_test_path


class UnsafePatch(ValueError):
    pass


@dataclass(frozen=True)
class PatchStats:
    files: tuple[str, ...]
    changed_lines: int
    byte_count: int


def validate_unified_diff(
    patch: str,
    *,
    allowed_files: set[str],
    max_bytes: int = 100_000,
    max_files: int = 40,
) -> PatchStats:
    encoded = patch.encode("utf-8")
    if not patch.strip():
        raise UnsafePatch("Patch is empty")
    if len(encoded) > max_bytes:
        raise UnsafePatch("Patch exceeds the configured byte limit")
    if "\x00" in patch or "GIT binary patch" in patch or "Binary files " in patch:
        raise UnsafePatch("Binary patches are not supported")

    files: list[str] = []
    changed_lines = 0
    current_file: str | None = None
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                raise UnsafePatch("Malformed diff header")
            old_path = parts[2][2:]
            new_path = parts[3][2:]
            if old_path != new_path:
                raise UnsafePatch("Renames and cross-path patches are not supported")
            _validate_patch_path(new_path, allowed_files)
            if new_path in files:
                raise UnsafePatch("Patch contains duplicate file sections")
            files.append(new_path)
            current_file = new_path
            if len(files) > max_files:
                raise UnsafePatch("Patch changes too many files")
        elif line.startswith(("+++ ", "--- ")):
            path = line[4:]
            if path == "/dev/null":
                raise UnsafePatch("Creating or deleting files is not supported")
            if not path.startswith(("a/", "b/")):
                raise UnsafePatch("Malformed patch path")
            _validate_patch_path(path[2:], allowed_files)
            if path[2:] != current_file:
                raise UnsafePatch("Patch headers disagree about the changed file")
        elif line.startswith(("old mode ", "new mode ", "new file mode ", "deleted file mode ")):
            raise UnsafePatch("Patch cannot change file modes or create/delete files")
        elif line.startswith(("+", "-")):
            changed_lines += 1

    if not files:
        raise UnsafePatch("Patch does not contain a unified diff header")
    return PatchStats(tuple(files), changed_lines, len(encoded))


def build_apply_command(patch: str) -> str:
    payload = base64.b64encode(patch.encode("utf-8")).decode("ascii")
    return (
        "set -eu; "
        "printf '%s' '"
        + payload
        + "' | base64 -d > /tmp/branchshift.patch; "
        "repo_root=$(git rev-parse --show-toplevel); "
        "repo_prefix=$(git rev-parse --show-prefix); "
        "if [ -n \"$repo_prefix\" ]; then "
        "git -C \"$repo_root\" apply --check --directory=\"${repo_prefix%/}\" "
        "/tmp/branchshift.patch; "
        "git -C \"$repo_root\" apply --directory=\"${repo_prefix%/}\" /tmp/branchshift.patch; "
        "else git apply --check /tmp/branchshift.patch; git apply /tmp/branchshift.patch; fi"
    )


def _validate_patch_path(path: str, allowed_files: set[str]) -> None:
    if not path or "\\" in path:
        raise UnsafePatch("Patch path is empty or uses backslashes")
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise UnsafePatch("Patch path escapes the repository")
    normalized = candidate.as_posix()
    if normalized == ".git" or normalized.startswith(".git/"):
        raise UnsafePatch("Patch cannot modify Git metadata")
    if is_test_path(normalized):
        raise UnsafePatch("Patch cannot modify protected test files")
    if normalized not in allowed_files:
        raise UnsafePatch(f"Patch changes an undeclared file: {normalized}")
