import json
import shlex
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.orchestrator.behavior_probes import (
    MAX_RESULT_BYTES,
    PROBE_MARKER,
    BehaviorProbeCase,
    BehaviorProbeObservation,
    BehaviorProbeResults,
    BehaviorProbeSuite,
    build_probe_command,
    compare_behavior_probes,
    parse_probe_output,
    probe_suite_digest,
)
from app.providers.redaction import redact


def suite(payload=None, **overrides):
    return BehaviorProbeSuite(cases=[BehaviorProbeCase(
        id="numeric-name", module="owned_probe_models", model="User",
        payload={"name": 123} if payload is None else payload, **overrides,
    )])


def run_owned_fixture(tmp_path, declaration, source, command=None):
    """Only our synthetic fixture executes locally; production helper only emits a command."""
    (tmp_path / "owned_probe_models.py").write_text(source)
    args = shlex.split(command or build_probe_command(declaration))
    assert args[:4] == [".venv/bin/python", "-I", "-B", "-c"]
    args[0] = sys.executable
    # Sandbox installs the real project. Tests expose only their own temporary module.
    args[4] = f"import sys; sys.path.insert(0, {str(tmp_path)!r})\n" + args[4]
    executed = subprocess.run(args, capture_output=True, text=True, timeout=5, check=True)
    assert executed.stderr == ""
    assert executed.stdout.count(PROBE_MARKER) == 1
    assert len(executed.stdout.splitlines()) == 1
    return parse_probe_output(executed.stdout, declaration)


def test_numeric_string_regression_is_review_difference_not_migration_failure(tmp_path):
    declared = suite()
    baseline = run_owned_fixture(tmp_path, declared, (
        "from pydantic.v1 import BaseModel\nclass User(BaseModel):\n    name: str\n"
    ))
    candidate = run_owned_fixture(tmp_path, declared, (
        "from pydantic import BaseModel\nclass User(BaseModel):\n    name: str\n"
    ))
    assert baseline.observations[0].value == {"name": "123"}
    assert candidate.observations[0].status == "rejected"
    assert candidate.observations[0].error_type == "ValidationError"
    comparison = compare_behavior_probes(baseline, candidate)
    assert comparison.review_only is True
    assert comparison.cases[0].status == "different"
    assert comparison.cases[0].basis == "acceptance"
    assert "migration" not in comparison.model_dump()


def test_alias_dump_and_printing_import_validator_serializer_do_not_spoof_marker(tmp_path):
    declaration = suite({"publicName": "Ada"})
    result = run_owned_fixture(tmp_path, declaration, f'''
import os, sys
from pydantic import BaseModel, Field, field_validator, field_serializer
print({PROBE_MARKER!r} + '{{"fake":true}}')
print('private import diagnostics', file=sys.stderr)
os.write(1, b'fd output should be discarded\\n')
sys.__stdout__.write('buffered output should be discarded\\n')
class User(BaseModel):
    name: str = Field(alias='publicName')
    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        print('validator noise')
        return value
    @field_serializer('name')
    def serialize_name(self, value):
        print('serializer noise')
        return value
''')
    assert result.observations[0].value == {"publicName": "Ada"}
    assert result.observations[0].status == "accepted"


@pytest.mark.parametrize("source, status, reason", [
    ("raise RuntimeError('do not leak /private/local/file')", "unsupported",
     "import_or_model_unavailable"),
    ("class User: pass", "unsupported", "not_pydantic_model"),
    ("from pydantic import BaseModel\nclass User(BaseModel):\n"
     "    name: str = 'Ada'\n    def model_dump_json(self, **kwargs):\n"
     "        raise ValueError('do not leak /private/local/file')\n", "unsupported",
     "serialization_failed"),
    ("from pydantic import BaseModel\nclass User(BaseModel):\n"
     "    name: str = 'x' * 5000\n", "unsupported", "output_limit"),
    ("raise SystemExit('do not leak /private/local/file')", "unsupported",
     "execution_interrupted"),
])
def test_unavailable_models_and_unserializable_outputs_are_unknown_not_rejected(
    tmp_path, source, status, reason,
):
    result = run_owned_fixture(tmp_path, suite({}), source)
    observation = result.observations[0]
    assert observation.status == status and observation.reason == reason
    assert observation.error_type is None and observation.value is None
    assert "/private/local/file" not in result.model_dump_json()
    assert compare_behavior_probes(result, result).cases[0].status == "unsupported"


def test_constructor_exception_retains_only_simple_class_not_message(tmp_path):
    result = run_owned_fixture(tmp_path, suite({"name": "Ada"}), '''
from pydantic import BaseModel, field_validator
class User(BaseModel):
    name: str
    @field_validator('name')
    @classmethod
    def reject(cls, value):
        raise TypeError('do not leak /private/local/file or token')
''')
    assert result.observations[0].status == "rejected"
    assert result.observations[0].error_type == "TypeError"
    assert "/private/local/file" not in result.model_dump_json()


@pytest.mark.parametrize("field, value", [
    ("module", "os;touch /tmp/unwanted"), ("module", "a..b"),
    ("model", "User.from_orm"), ("model", "User()"),
    ("id", "\nforged"), ("payload", ["not an object"]),
])
def test_declarations_reject_executable_names_or_non_object_payloads(field, value):
    data = suite().model_dump()
    data["cases"][0][field] = value
    with pytest.raises(ValidationError):
        BehaviorProbeSuite.model_validate(data)


def test_request_case_count_uniqueness_finite_json_and_aggregate_byte_bounds():
    with pytest.raises(ValidationError):
        BehaviorProbeSuite(cases=[])
    with pytest.raises(ValidationError):
        BehaviorProbeSuite(cases=suite().cases * 2)
    with pytest.raises(ValidationError):
        BehaviorProbeSuite(cases=[
            suite().cases[0].model_copy(update={"id": str(i)}) for i in range(13)
        ])
    with pytest.raises(ValidationError, match="16 KiB"):
        suite({"value": "x" * 16_384})
    with pytest.raises(ValidationError):
        suite({"number": float("nan")})


def test_command_freezes_payload_and_never_interpolates_it_as_code(tmp_path):
    payload = {"name": "$(touch /tmp/unwanted); ' \\\n{not code}"}
    declared = suite(payload)
    command = build_probe_command(declared)
    frozen = BehaviorProbeSuite.model_validate(declared.model_dump())
    declared.cases[0].payload["name"] = "different later input"
    assert "touch /tmp/unwanted" not in command
    result = run_owned_fixture(tmp_path, frozen, (
        "from pydantic import BaseModel\nclass User(BaseModel):\n    name: str\n"
    ), command)
    assert result.observations[0].value == payload
    declared.cases[0].payload["name"] = "x" * 20_000
    with pytest.raises(ValueError, match="16 KiB"):
        build_probe_command(declared)


def results(declared, *, value=None, status="accepted", error_type=None, reason=None):
    return BehaviorProbeResults(
        suite_digest=probe_suite_digest(declared), observations=[BehaviorProbeObservation(
            id=declared.cases[0].id, status=status, value=value,
            error_type=error_type, reason=reason,
        )],
    )


@pytest.mark.parametrize("before, after, expected", [
    ({"a": 1, "b": [None]}, {"b": [None], "a": 1}, "match"),
    ({"a": 1}, {"a": True}, "different"),
    ({"a": 1}, {"a": 1.0}, "different"),
    ({"items": [1, 2]}, {"items": [2, 1]}, "different"),
    (None, None, "match"),
])
def test_exact_json_comparison_preserves_types_and_order_without_flattening(
    before, after, expected,
):
    declaration = suite()
    comparison = compare_behavior_probes(results(declaration, value=before),
                                         results(declaration, value=after))
    assert comparison.cases[0].status == expected


def test_parser_requires_unique_bounded_complete_frozen_evidence():
    declaration = suite()
    valid = results(declaration, value={"name": "123"}).model_dump(mode="json")
    marker = PROBE_MARKER + json.dumps(valid)
    assert parse_probe_output(marker, declaration).observations[0].value == {"name": "123"}
    for output in ("", marker + "\n" + marker, PROBE_MARKER + "x" * MAX_RESULT_BYTES):
        with pytest.raises(ValueError):
            parse_probe_output(output, declaration)
    for field, value in (("suite_digest", "f" * 64), ("observations", [])):
        changed = valid | {field: value}
        with pytest.raises(ValueError):
            parse_probe_output(PROBE_MARKER + json.dumps(changed), declaration)
    valid["observations"][0]["id"] = "other"
    with pytest.raises(ValueError, match="cases"):
        parse_probe_output(PROBE_MARKER + json.dumps(valid), declaration)
    with pytest.raises(ValueError, match="frozen"):
        compare_behavior_probes(results(declaration), results(suite({"name": "other"})))


def test_invalid_observation_cannot_claim_acceptance_or_zero_unknown_output():
    for data in (
        {"id": "case", "status": "accepted"},
        {"id": "case", "status": "accepted", "value": float("inf")},
        {"id": "case", "status": "accepted", "value": "x" * 4097},
        {"id": "case", "status": "rejected"},
        {"id": "case", "status": "unsupported"},
        {"id": "case", "status": "rejected", "error_type": "<script>"},
    ):
        with pytest.raises(ValidationError):
            BehaviorProbeObservation.model_validate(data)


def test_aggregate_output_over_16000_bytes_is_unknown_not_truncated_success(tmp_path):
    declared = BehaviorProbeSuite(cases=[BehaviorProbeCase(
        id=f"case-{index}", module="owned_probe_models", model="User", payload={},
    ) for index in range(12)])
    (tmp_path / "owned_probe_models.py").write_text(
        "from pydantic import BaseModel\nclass User(BaseModel):\n    name: str = 'x' * 2000\n"
    )
    args = shlex.split(build_probe_command(declared))
    args[0] = sys.executable
    args[4] = f"import sys; sys.path.insert(0, {str(tmp_path)!r})\n" + args[4]
    executed = subprocess.run(args, capture_output=True, text=True, timeout=5)
    assert executed.returncode != 0
    assert executed.stdout == "" and executed.stderr == ""
    with pytest.raises(ValueError, match="missing"):
        parse_probe_output(executed.stdout, declared)
    output = {
        "suite_digest": probe_suite_digest(declared),
        "observations": [
            {"id": case.id, "status": "accepted", "value": {"name": "x" * 2000}}
            for case in declared.cases
        ],
    }
    with pytest.raises(ValueError, match="oversized"):
        parse_probe_output(PROBE_MARKER + json.dumps(output), declared)


def test_provider_redaction_cannot_turn_distinct_json_outputs_into_a_match():
    declaration = suite()
    transported = []
    for value in ("sk-" + "a" * 20, "sk-" + "b" * 20):
        raw = PROBE_MARKER + results(declaration, value={"name": value}).model_dump_json()
        transported.append(redact(raw))
    assert transported[0] == transported[1]
    for output in transported:
        with pytest.raises(ValueError, match="redacted; comparison is unavailable"):
            parse_probe_output(output, declaration)
