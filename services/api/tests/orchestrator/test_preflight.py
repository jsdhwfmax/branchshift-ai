import pytest

from app.orchestrator.patches import UnsafePatch
from app.orchestrator.preflight import validate_replacement_source

MANIFEST = '''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "fixture"
version = "0.1.0"
dependencies = ["pydantic>=1.10,<2", "httpx>=0.28"]
[project.optional-dependencies]
test = ["pytest>=8"]
[tool.pytest.ini_options]
testpaths = ["tests"]
'''


def test_python_preflight_never_executes_code(tmp_path):
    marker = tmp_path / "must-not-exist"
    code = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
    validate_replacement_source("src/model.py", "", code)
    assert not marker.exists()


def test_python_syntax_diagnostic_contains_file_line_and_actual_problem():
    with pytest.raises(UnsafePatch, match="src/model.py:1: invalid Python"):
        validate_replacement_source("src/model.py", "", "def invalid(:\n    pass\n")


def test_quote_stripping_is_rejected_as_toml_parse_failure():
    broken = MANIFEST.replace('"setuptools>=68"', "setuptools>=68")
    with pytest.raises(UnsafePatch, match="invalid TOML.*Preserve quotes"):
        validate_replacement_source("pyproject.toml", MANIFEST, broken)


def test_pydantic_constraint_is_the_only_permitted_manifest_change():
    validate_replacement_source(
        "pyproject.toml", MANIFEST, MANIFEST.replace("pydantic>=1.10,<2", "pydantic>=2,<3")
    )


@pytest.mark.parametrize(
    "old, new",
    [
        ('version = "0.1.0"', 'version = "0.2.0"'),
        ('["tests"]', '["other"]'),
        ('"setuptools>=68"', '"setuptools>=99"'),
        ('"httpx>=0.28"', '"httpx>=1"'),
        ('test = ["pytest>=8"]', 'test = "pytest>=8"'),
    ],
)
def test_unrelated_manifest_changes_fail_before_execution(old, new):
    with pytest.raises(UnsafePatch):
        validate_replacement_source("pyproject.toml", MANIFEST, MANIFEST.replace(old, new))
