"""Explicit, bounded model examples for maintainer review, never an equivalence gate.

Only build commands here: repository imports and validators must run in a Sandbox with
an external timeout. The command embeds a frozen JSON declaration, not executable input.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

MAX_CASES = 12
MAX_INPUT_BYTES = 16_384
MAX_VALUE_BYTES = 4_096
MAX_RESULT_BYTES = 16_000
PROBE_MARKER = "__BRANCHSHIFT_BEHAVIOR_PROBES_V1="
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=100)]
CaseID = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=64)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


class _ProbeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BehaviorProbeCase(_ProbeModel):
    id: CaseID
    module: str = Field(
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$",
        max_length=200,
    )
    model: Identifier
    payload: dict[str, JsonValue]


class BehaviorProbeSuite(_ProbeModel):
    cases: list[BehaviorProbeCase] = Field(min_length=1, max_length=MAX_CASES)

    @model_validator(mode="after")
    def bounded_unique_cases(self) -> BehaviorProbeSuite:
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Behavior probe case IDs must be unique")
        if len(_json_bytes(self.model_dump(mode="json"))) > MAX_INPUT_BYTES:
            raise ValueError("Behavior probe declarations exceed 16 KiB")
        return self


class BehaviorProbeObservation(_ProbeModel):
    id: CaseID
    status: Literal["accepted", "rejected", "unsupported"]
    value: JsonValue = None
    error_type: Identifier | None = None
    reason: Literal[
        "import_or_model_unavailable", "not_pydantic_model", "serialization_failed",
        "output_limit", "execution_interrupted",
    ] | None = None

    @model_validator(mode="after")
    def consistent_observation(self) -> BehaviorProbeObservation:
        if self.status == "accepted":
            if "value" not in self.model_fields_set or self.error_type or self.reason:
                raise ValueError("An accepted probe needs a JSON value and no error")
            if len(_json_bytes(self.value)) > MAX_VALUE_BYTES:
                raise ValueError("Behavior probe output exceeds 4 KiB")
        elif self.status == "rejected":
            if not self.error_type or self.value is not None or self.reason:
                raise ValueError("A rejected probe needs only an error class")
        elif not self.reason or self.value is not None or self.error_type:
            raise ValueError("An unsupported probe needs only a bounded reason")
        return self


class BehaviorProbeResults(_ProbeModel):
    suite_digest: Digest
    observations: list[BehaviorProbeObservation] = Field(min_length=1, max_length=MAX_CASES)

    @model_validator(mode="after")
    def unique_results(self) -> BehaviorProbeResults:
        if len({item.id for item in self.observations}) != len(self.observations):
            raise ValueError("Behavior probe result IDs must be unique")
        return self


class BehaviorProbeCaseComparison(_ProbeModel):
    id: CaseID
    status: Literal["match", "different", "unsupported"]
    basis: Literal["same_observation", "acceptance", "json_output", "error_type", "unavailable"]


class BehaviorProbeComparison(_ProbeModel):
    suite_digest: Digest
    review_only: Literal[True] = True
    cases: list[BehaviorProbeCaseComparison] = Field(min_length=1, max_length=MAX_CASES)


def _frozen_suite(suite: BehaviorProbeSuite) -> tuple[BehaviorProbeSuite, bytes]:
    # Revalidate a copy: frozen models cannot prevent in-place changes to nested JSON/list values.
    copied = BehaviorProbeSuite.model_validate(suite.model_dump(mode="json"))
    return copied, _json_bytes(copied.model_dump(mode="json"))


def probe_suite_digest(suite: BehaviorProbeSuite) -> str:
    return hashlib.sha256(_frozen_suite(suite)[1]).hexdigest()


# This is fixed trusted adapter code. No repository name, class name or payload is code.
_PROBE_SCRIPT = r'''
import base64, contextlib, hashlib, importlib, json, os, re, sys
raw = base64.b64decode(sys.argv[1], validate=True)
suite = json.loads(raw)
observations = []
saved_stdout, saved_stderr = os.dup(1), os.dup(2)
try:
    with open(os.devnull, 'w') as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            for case in suite['cases']:
                row = {'id': case['id'], 'status': 'unsupported',
                       'reason': 'import_or_model_unavailable'}
                try:
                    pydantic = importlib.import_module('pydantic')
                    bases = [pydantic.BaseModel]
                    try:
                        bases.append(importlib.import_module('pydantic.v1').BaseModel)
                    except ImportError:
                        pass
                    module = importlib.import_module(case['module'])
                    model = getattr(module, case['model'])
                    if not isinstance(model, type) or not issubclass(model, tuple(bases)):
                        row['reason'] = 'not_pydantic_model'
                    else:
                        try:
                            instance = model(**case['payload'])
                        except Exception as exc:
                            name = type(exc).__name__
                            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,99}', name):
                                name = 'Exception'
                            row = {'id': case['id'], 'status': 'rejected', 'error_type': name}
                        else:
                            row['reason'] = 'serialization_failed'
                            dump = getattr(instance, 'model_dump_json', None)
                            encoded = dump(by_alias=True) if callable(dump) else instance.json(
                                by_alias=True)
                            if len(encoded.encode('utf-8')) > 4096:
                                row['reason'] = 'output_limit'
                            else:
                                value = json.loads(encoded)
                                normalized = json.dumps(value, sort_keys=True,
                                    separators=(',', ':'), ensure_ascii=True, allow_nan=False)
                                if len(normalized.encode('ascii')) > 4096:
                                    row['reason'] = 'output_limit'
                                else:
                                    row = {'id': case['id'], 'status': 'accepted', 'value': value}
                except Exception:
                    pass
                except BaseException:
                    row = {'id': case['id'], 'status': 'unsupported',
                           'reason': 'execution_interrupted'}
                observations.append(row)
finally:
    sys.__stdout__.flush()
    sys.__stderr__.flush()
    os.dup2(saved_stdout, 1)
    os.dup2(saved_stderr, 2)
    os.close(saved_stdout)
    os.close(saved_stderr)
result = {'suite_digest': hashlib.sha256(raw).hexdigest(), 'observations': observations}
encoded = json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                     allow_nan=False)
if len(('__BRANCHSHIFT_BEHAVIOR_PROBES_V1=' + encoded).encode('ascii')) > 16000:
    raise SystemExit(1)
print('__BRANCHSHIFT_BEHAVIOR_PROBES_V1=' + encoded)
'''


def build_probe_command(suite: BehaviorProbeSuite) -> str:
    """Run from the installed project directory in Sandbox, with an external timeout."""
    _, raw = _frozen_suite(suite)
    encoded = base64.b64encode(raw).decode("ascii")
    return ".venv/bin/python -I -B -c " + shlex.quote(_PROBE_SCRIPT) + " " + shlex.quote(encoded)


def parse_probe_output(output: str, suite: BehaviorProbeSuite) -> BehaviorProbeResults:
    """Reject missing, duplicate or mismatched evidence; callers must retain unknown scope."""
    frozen, _ = _frozen_suite(suite)
    matches = re.findall(rf"^{re.escape(PROBE_MARKER)}([^\n]+)$", output, re.MULTILINE)
    if len(matches) != 1 or len((PROBE_MARKER + matches[0]).encode()) > MAX_RESULT_BYTES:
        raise ValueError("Behavior probe evidence is missing, ambiguous or oversized")
    # The provider redacts stdout before returning it. Distinct values may collapse to
    # this placeholder, so they cannot establish an exact JSON match (or difference).
    if "[REDACTED]" in matches[0]:
        raise ValueError("Behavior probe evidence was redacted; comparison is unavailable")
    result = BehaviorProbeResults.model_validate_json(matches[0])
    if result.suite_digest != probe_suite_digest(frozen):
        raise ValueError("Behavior probe evidence belongs to different frozen inputs")
    if [item.id for item in result.observations] != [case.id for case in frozen.cases]:
        raise ValueError("Behavior probe evidence has missing, extra or reordered cases")
    return result


def compare_behavior_probes(
    baseline: BehaviorProbeResults, candidate: BehaviorProbeResults,
) -> BehaviorProbeComparison:
    """Compare only explicit cases, preserving JSON types; never change migration status."""
    if baseline.suite_digest != candidate.suite_digest or (
        [item.id for item in baseline.observations] != [item.id for item in candidate.observations]
    ):
        raise ValueError("Only results from the same frozen behavior cases can be compared")
    cases = []
    for before, after in zip(baseline.observations, candidate.observations, strict=True):
        status: Literal["match", "different", "unsupported"] = "match"
        basis: Literal[
            "same_observation", "acceptance", "json_output", "error_type", "unavailable"
        ] = "same_observation"
        if "unsupported" in {before.status, after.status}:
            status, basis = "unsupported", "unavailable"
        elif before.status != after.status:
            status, basis = "different", "acceptance"
        elif before.status == "accepted" and _json_bytes(before.value) != _json_bytes(after.value):
            status, basis = "different", "json_output"
        elif before.status == "rejected" and before.error_type != after.error_type:
            status, basis = "different", "error_type"
        cases.append(BehaviorProbeCaseComparison(id=before.id, status=status, basis=basis))
    return BehaviorProbeComparison(suite_digest=baseline.suite_digest, cases=cases)
