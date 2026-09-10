import pytest
import tomlkit
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

from app.orchestrator.dependencies import migrate_pyproject_pydantic
from app.orchestrator.patches import UnsafePatch

MANIFEST = '''# Keep all project metadata and comments.
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "fixture"
version = "0.1.0"
dependencies = [
  'Pydantic[email,timezone]>=1.10,<2; python_version >= "3.10"', # important marker
  "pydantic-core>=2",  # different package
  "httpx>=0.28",
]

[project.optional-dependencies]
test = ["pytest>=8"]
legacy = ["pydantic == 1.10.21 ; sys_platform != 'win32'"]

[tool.pytest.ini_options]
testpaths = ["tests"]
'''


def test_only_pydantic_specifier_bytes_change_preserving_quotes_metadata_comments():
    updated = migrate_pyproject_pydantic(MANIFEST)
    assert updated == MANIFEST.replace(
        ">=1.10,<2", ">=2,<3"
    ).replace("== 1.10.21", ">=2,<3")
    original_project = tomlkit.parse(MANIFEST)["project"]
    updated_project = tomlkit.parse(updated)["project"]
    original = Requirement(original_project["dependencies"][0])
    actual = Requirement(updated_project["dependencies"][0])
    assert actual.specifier == SpecifierSet(">=2,<3")
    assert actual.name == original.name
    assert actual.extras == original.extras == {"email", "timezone"}
    assert actual.marker == original.marker


@pytest.mark.parametrize(
    "requirement, expected",
    [
        ("pydantic", "pydantic>=2,<3"),
        ("pydantic[email] ~= 1.10", "pydantic[email] >=2,<3"),
        ("pydantic (>=1.10,<2)", "pydantic >=2,<3"),
        ("pydantic>=2,<3", "pydantic>=2,<3"),
        ("pydantic<3,>=2", "pydantic<3,>=2"),
        ("pydantic>=2.11,<3", "pydantic>=2,<3"),
    ],
)
def test_requirement_forms_have_semantically_correct_v2_pin(requirement, expected):
    original = '[project]\ndependencies = ["' + requirement + '"]\n'
    assert migrate_pyproject_pydantic(original) == original.replace(requirement, expected)


@pytest.mark.parametrize("ending", ["", "\n", "\r\n"])
def test_unrelated_or_already_migrated_manifest_is_byte_identical(ending):
    original = '[project]\ndependencies = ["requests>=2", "pydantic<3,>=2"]' + ending
    assert migrate_pyproject_pydantic(original) == original


def test_no_pydantic_dependency_is_invented():
    original = '[project]\nname = "example"\ndependencies = ["requests>=2"]\n'
    assert migrate_pyproject_pydantic(original) == original


@pytest.mark.parametrize(
    "original, message",
    [
        ('[project]\ndependencies = [pydantic>=1]\n', "invalid TOML"),
        ('[project]\ndependencies = "pydantic<2"\n', "arrays"),
        ('[project]\ndependencies = [3]\n', "requirement strings"),
        ('[project]\ndependencies = ["not a valid requirement"]\n', "invalid dependency"),
        (
            '[project]\ndependencies = ["pydantic @ https://example.com/pydantic.whl"]\n',
            "direct URL",
        ),
    ],
)
def test_unsupported_manifest_is_rejected_without_reinterpreting_it(original, message):
    with pytest.raises(UnsafePatch, match=message):
        migrate_pyproject_pydantic(original)
