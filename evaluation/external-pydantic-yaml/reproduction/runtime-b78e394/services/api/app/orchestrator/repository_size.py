"""Trusted pre-install checkout acceptance gate, executed inside the Sandbox."""
from __future__ import annotations

import shlex

DEFAULT_MAX_REPOSITORY_BYTES = 50 * 1024 * 1024

_GUARD_SCRIPT = """
import os
import stat
import subprocess
import sys

root = os.fsencode(sys.argv[1])
limit = int(sys.argv[2])
total = 0
try:
    listing = subprocess.run(
        ["git", "-C", os.fsdecode(root), "ls-files", "--stage", "-z"],
        capture_output=True, check=True,
    ).stdout
    if listing and not listing.endswith(b"\\0"):
        raise ValueError("Incomplete tracked-file listing")
    for entry in listing.split(b"\\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\\t", 1)
        mode, object_id, stage = metadata.split()
        if (
            stage != b"0" or mode not in (b"100644", b"100755", b"120000")
            or path.startswith(b"/")
            or any(part in (b"", b".", b"..") for part in path.split(b"/"))
        ):
            raise ValueError("Unsupported tracked-file entry")
        info = os.lstat(os.path.join(root, path))
        if not (
            (mode == b"120000" and stat.S_ISLNK(info.st_mode))
            or (mode != b"120000" and stat.S_ISREG(info.st_mode))
        ):
            raise ValueError("Tracked-file type differs from the Git index")
        total += info.st_size
        if total > limit:
            print(
                "Repository tracked checkout exceeds configured limit: "
                f"observed at least {total} bytes; limit {limit} bytes",
                file=sys.stderr,
            )
            sys.exit(1)
except (OSError, ValueError, subprocess.SubprocessError):
    print("Repository tracked checkout size could not be verified", file=sys.stderr)
    sys.exit(1)
print(f"__BRANCHSHIFT_TRACKED_CHECKOUT_BYTES={total}")
print(f"__BRANCHSHIFT_MAX_REPOSITORY_BYTES={limit}")
"""


def repository_size_guard_command(
    root: str, max_bytes: int = DEFAULT_MAX_REPOSITORY_BYTES,
) -> str:
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("MAX_REPOSITORY_BYTES must be a positive integer")
    # -I prevents Python from importing repository modules through cwd/PYTHONPATH.
    return (
        f"python -I -c {shlex.quote(_GUARD_SCRIPT)} "
        f"{shlex.quote(root)} {max_bytes}"
    )
