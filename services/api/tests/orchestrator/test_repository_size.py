import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.domain.models import http_url
from app.orchestrator import baseline
from app.orchestrator.repository_size import (
    DEFAULT_MAX_REPOSITORY_BYTES,
    repository_size_guard_command,
)


def track(root, contents):
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    for name, data in contents.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    subprocess.run(["git", "-C", str(root), "add", "--all"], check=True, capture_output=True)


def check_size(root, limit):
    env = os.environ.copy()
    env["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["sh", "-c", repository_size_guard_command(str(root), limit)],
        capture_output=True, text=True, env=env, cwd=root,
    )


@pytest.mark.parametrize("limit, accepted", [(12, True), (11, False)])
def test_tracked_byte_limit_accepts_equal_and_rejects_one_extra_byte(tmp_path, limit, accepted):
    root = tmp_path / "repo"
    track(root, {"first.txt": b"a" * 5, "second.txt": b"b" * 7})
    result = check_size(root, limit)
    assert (result.returncode == 0) is accepted
    if accepted:
        assert "__BRANCHSHIFT_TRACKED_CHECKOUT_BYTES=12\n" in result.stdout
        assert "__BRANCHSHIFT_MAX_REPOSITORY_BYTES=12\n" in result.stdout
    else:
        assert "exceeds configured limit" in result.stderr
        assert "limit 11 bytes" in result.stderr


def test_nul_delimited_names_are_not_executed_or_split(tmp_path):
    root = tmp_path / "repo"
    contents = {
        "line\nbreak": b"12", "tab\tname": b"345", "space name": b"6",
        "$(touch ATTACKED)": b"7", "quote'and;semicolon": b"89", "--option": b"0",
        "subprocess.py": b"raise RuntimeError('Repository module must not be imported')\n",
    }
    track(root, contents)
    result = check_size(root, sum(map(len, contents.values())))
    assert result.returncode == 0, result.stderr
    assert not (root / "ATTACKED").exists()


@pytest.mark.parametrize("dangling", [False, True])
def test_symlink_counts_only_link_bytes_without_following_target(tmp_path, dangling):
    root = tmp_path / "repo"
    track(root, {"small": b"1"})
    outside = tmp_path / "outside"
    if not dangling:
        outside.write_bytes(b"x" * 10_000)
    link = root / "link"
    link.symlink_to(outside)
    subprocess.run(["git", "-C", str(root), "add", "--all"], check=True, capture_output=True)
    expected = 1 + link.lstat().st_size
    result = check_size(root, expected)
    assert result.returncode == 0, result.stderr
    assert f"__BRANCHSHIFT_TRACKED_CHECKOUT_BYTES={expected}\n" in result.stdout
    assert check_size(root, expected - 1).returncode != 0


@pytest.mark.parametrize("problem", ["missing", "type-changed", "git-error", "submodule"])
def test_unverifiable_tracked_checkout_fails_closed(tmp_path, problem):
    root = tmp_path / "repo"
    track(root, {"tracked": b"1"})
    if problem == "missing":
        (root / "tracked").unlink()
    elif problem == "type-changed":
        (root / "tracked").unlink()
        (root / "tracked").symlink_to(tmp_path / "outside")
    elif problem == "git-error":
        shutil.rmtree(root / ".git")
    else:
        subprocess.run([
            "git", "-C", str(root), "update-index", "--add", "--cacheinfo",
            f"160000,{'1' * 40},submodule",
        ], check=True, capture_output=True)
    result = check_size(root, 1_000_000)
    assert result.returncode != 0
    assert "size could not be verified" in result.stderr
    assert "TRACKED_CHECKOUT_BYTES=" not in result.stdout


@pytest.mark.parametrize("accepted", [False, True])
def test_setup_checks_entire_checkout_before_venv_and_install(tmp_path, monkeypatch, accepted):
    root = tmp_path / "repo"
    manifest = b"[project]\nname = 'controlled-fixture'\n"
    track(root, {"project/pyproject.toml": manifest, "elsewhere/large.bin": b"x" * 100})
    monkeypatch.setattr(baseline, "REPOSITORY_ROOT", str(root))
    limit = len(manifest) + (100 if accepted else 99)
    marker = tmp_path / "installed"
    venv_marker = tmp_path / "venv-created"
    clone_marker = tmp_path / "clone-called"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    real_git = shutil.which("git")
    assert real_git is not None
    fake_git = fake_bin / "git"
    fake_git.write_text(
        f"#!{sys.executable}\nimport os, sys\nfrom pathlib import Path\n"
        "if sys.argv[1] == 'clone':\n"
        f"    Path({str(clone_marker)!r}).write_text('synthetic clone')\n"
        "else:\n"
        f"    os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n"
    )
    installer = f"#!/bin/sh\nprintf installed > {shlex.quote(str(marker))}\n"
    fake_python = fake_bin / "python"
    fake_python.write_text(
        f"#!{sys.executable}\nimport os, sys\nfrom pathlib import Path\n"
        "if sys.argv[1:3] == ['-m', 'venv']:\n"
        f"    Path({str(venv_marker)!r}).write_text('synthetic venv')\n"
        "    target = Path('.venv/bin/python')\n"
        "    target.parent.mkdir(parents=True)\n"
        f"    target.write_text({installer!r})\n"
        "    target.chmod(0o755)\n"
        "else:\n"
        f"    os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n"
    )
    fake_git.chmod(0o755)
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    command = baseline.build_setup_command(
        http_url("https://github.com/owner/repo"), str(root / "project"), limit,
    )
    result = subprocess.run(["sh", "-c", command], capture_output=True, text=True, env=env)
    assert clone_marker.exists()
    assert (result.returncode == 0) is accepted, result.stderr
    assert venv_marker.exists() is accepted
    assert marker.exists() is accepted
    if not accepted:
        assert "exceeds configured limit" in result.stderr


@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_direct_repository_limit_must_be_a_positive_integer(value):
    with pytest.raises(ValueError, match="MAX_REPOSITORY_BYTES"):
        Settings(max_repository_bytes=value)
    with pytest.raises(ValueError, match="MAX_REPOSITORY_BYTES"):
        repository_size_guard_command("/workspace/repo", value)


@pytest.mark.parametrize("value", ["0", "-1", "invalid", "1.5"])
def test_environment_repository_limit_cannot_silently_fall_back(tmp_path, value):
    env = os.environ.copy()
    env["MAX_REPOSITORY_BYTES"] = value
    result = subprocess.run(
        [sys.executable, "-c", "from app.config import Settings; Settings()"],
        capture_output=True, text=True, env=env, cwd=tmp_path,
    )
    assert result.returncode != 0
    assert "ValueError" in result.stderr


def test_default_repository_limit_is_fifty_mib():
    assert Settings().max_repository_bytes == DEFAULT_MAX_REPOSITORY_BYTES == 52_428_800
