import base64
import subprocess

import pytest

from app.orchestrator.patches import UnsafePatch, build_apply_command, validate_unified_diff

VALID_PATCH = """diff --git a/src/app/models.py b/src/app/models.py
index 1234567..7654321 100644
--- a/src/app/models.py
+++ b/src/app/models.py
@@ -1,2 +1,2 @@
-from pydantic import validator
+from pydantic import field_validator
 class User: ...
"""


def test_valid_patch_returns_bounded_metrics():
    stats = validate_unified_diff(VALID_PATCH, allowed_files={"src/app/models.py"})
    assert stats.files == ("src/app/models.py",)
    assert stats.changed_lines == 2
    assert stats.byte_count == len(VALID_PATCH.encode())


@pytest.mark.parametrize(
    "patch, message",
    [
        (
            VALID_PATCH.replace("src/app/models.py", "../secrets.env"),
            "escapes the repository",
        ),
        (
            VALID_PATCH.replace("src/app/models.py", ".git/config"),
            "Git metadata",
        ),
        (
            VALID_PATCH.replace("src/app/models.py", "src/app/unknown.py"),
            "undeclared file",
        ),
        ("GIT binary patch\n" + VALID_PATCH, "Binary patches"),
        ("not a patch", "unified diff header"),
    ],
)
def test_unsafe_patch_shapes_fail_closed(patch, message):
    with pytest.raises(UnsafePatch, match=message):
        validate_unified_diff(patch, allowed_files={"src/app/models.py"})


def test_oversized_patch_is_rejected():
    with pytest.raises(UnsafePatch, match="byte limit"):
        validate_unified_diff(
            VALID_PATCH,
            allowed_files={"src/app/models.py"},
            max_bytes=10,
        )


def test_apply_command_transports_patch_without_shell_interpolation():
    dangerous = VALID_PATCH + "\n# $(touch /tmp/should-not-run) `id`\n"
    command = build_apply_command(dangerous)
    assert "$(touch" not in command
    assert "`id`" not in command
    payload = command.split("'")[3]
    assert base64.b64decode(payload).decode() == dangerous


@pytest.mark.parametrize("path", ["tests/test_models.py", "conftest.py", "src/test_api.py"])
def test_test_files_are_protected_even_if_model_declares_them(path):
    with pytest.raises(UnsafePatch, match="protected test"):
        validate_unified_diff(
            VALID_PATCH.replace("src/app/models.py", path), allowed_files={path}
        )


@pytest.mark.parametrize("nested", [False, True])
def test_git_actually_applies_project_relative_patch(tmp_path, nested):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    project = tmp_path / "fixtures" / "target" if nested else tmp_path
    target = project / "src" / "app" / "models.py"
    target.parent.mkdir(parents=True)
    target.write_text("from pydantic import validator\nclass User: ...\n")
    # Only the deterministic patch is executed; no repository code is run on the host.
    applied = subprocess.run(
        ["sh", "-c", build_apply_command(VALID_PATCH).replace(
            "/tmp/branchshift.patch", str(tmp_path / "candidate.patch")
        )], cwd=project,
        capture_output=True, text=True,
    )
    assert applied.returncode == 0, applied.stderr
    assert target.read_text() == "from pydantic import field_validator\nclass User: ...\n"


def test_mismatched_patch_headers_cannot_hide_changed_file():
    patch = VALID_PATCH.replace("+++ b/src/app/models.py", "+++ b/src/app/other.py")
    with pytest.raises(UnsafePatch, match="headers disagree"):
        validate_unified_diff(patch, allowed_files={"src/app/models.py", "src/app/other.py"})
