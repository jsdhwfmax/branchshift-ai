"""Host-safe checks: fixture text is parsed, never imported or executed here."""
import ast
import builtins
import hashlib
import json
import os
import shutil
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

from app.cli.security_probes import (
    ADAPTER_OUTPUT_LIMIT,
    ADAPTER_SOURCE,
    CASE_IDS,
    DEFAULT_FIXTURES,
    HOST_CANARY_ENV,
    MARKER,
    SAFETY_MARKER,
    build_probe_command,
    execute_probes,
    inspection_report,
    load_probes,
    main,
    observation_from_result,
    runtime_metadata,
    synthetic_host_canary,
)
from app.domain.models import BranchStatus, MigrationStrategy
from app.orchestrator.branch_runner import BranchRunner, FileReplacement, PatchProposal
from app.orchestrator.planner import RepositoryEvidence
from app.providers.base import CommandResult, SandboxState


def test_six_reviewed_fixtures_are_data_with_bounded_source_and_no_live_claim():
    probes = load_probes()
    assert tuple(p.id for p in probes) == CASE_IDS
    assert all(p.file.endswith(".py.txt") for p in probes)
    assert all(len(p.source.encode()) <= 16_000 for p in probes)
    report = inspection_report(probes)
    assert report["remote_execution"] == "not_performed"
    assert report["remote_run_calls_planned"] == 5
    assert report["model_calls_planned"] == 0


def test_default_cli_inspects_without_importing_credentials_or_providers(monkeypatch, capsys):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name in {"app.config", "app.providers.contree"}:
            raise AssertionError("Default inspection must not load credentials or providers")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr("sys.argv", ["security_probes"])
    main()
    assert json.loads(capsys.readouterr().out)["remote_execution"] == "not_performed"


def test_report_fingerprints_actual_installed_sdk_and_adapter_source():
    metadata = runtime_metadata()
    assert metadata["sdk_distribution"] == "contree-sdk"
    assert metadata["sdk_version"] == version("contree-sdk")
    expected_hash = hashlib.sha256(ADAPTER_SOURCE.read_bytes()).hexdigest()
    assert metadata["adapter_source_sha256"] == expected_hash
    assert len(metadata["probe_runner_sha256"]) == 64


def test_missing_sdk_metadata_is_unknown_without_loading_provider(monkeypatch):
    def missing(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr("app.cli.security_probes.version", missing)
    assert runtime_metadata()["sdk_version"] is None


@pytest.mark.parametrize(
    "field, value", [("file", "../../.env"), ("timeout_seconds", 300), ("mode", "host")]
)
def test_manifest_cannot_expand_the_reviewed_path_timeout_or_mode(tmp_path, field, value):
    root = tmp_path / "fixtures"
    shutil.copytree(DEFAULT_FIXTURES, root)
    manifest = json.loads((root / "cases.json").read_text())
    manifest["cases"][1][field] = value
    (root / "cases.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        load_probes(root)


def test_fixture_symlink_cannot_escape_its_directory(tmp_path):
    root = tmp_path / "fixtures"
    shutil.copytree(DEFAULT_FIXTURES, root)
    external = tmp_path / "external.py.txt"
    external.write_text("raise AssertionError('Never executed')\n")
    source = root / "fixtures/host_path.py.txt"
    source.unlink()
    source.symlink_to(external)
    with pytest.raises(ValueError, match="outside"):
        load_probes(root)


def test_remote_commands_have_independent_alarm_and_guard_before_fixture_text():
    path = Path("/tmp/branchshift-security-test/host-only-canary.txt")
    for probe in load_probes()[1:]:
        command = build_probe_command(probe, path)
        script = command.split("\n", 1)[1].rsplit("\n", 1)[0]
        ast.parse(script)  # Never run the assembled Python or shell on this host.
        assert script.index("signal.alarm(8)") < script.index(probe.source)
        assert script.index("marker.read_text()") < script.index(probe.source)
        assert "remote-only-marker" in script
    with pytest.raises(ValueError, match="not executed"):
        build_probe_command(load_probes()[0], path)


@pytest.mark.parametrize("path", ["/etc/passwd", "/tmp/../root/host-only-canary.txt", "/.env"])
def test_host_path_probe_refuses_any_non_canary_path(path):
    with pytest.raises(ValueError, match="synthetic"):
        build_probe_command(load_probes()[3], Path(path))


def test_fixture_scope_uses_no_host_secrets_or_process_launches():
    for probe in load_probes()[1:]:
        tree = ast.parse(probe.source)
        imported = {
            alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        assert imported <= {"os", "pathlib", "sys", "time", "http.client"}
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert not names & {"exec", "eval", "compile", "subprocess", "__import__"}
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert not attributes & {"fork", "system", "popen", "iterdir", "glob", "walk"}
        assert "NEBIUS_API_KEY" not in probe.source
        assert "TAVILY_API_KEY" not in probe.source
        assert ".ssh" not in probe.source and "/Users/" not in probe.source


def test_network_fixture_has_exactly_one_public_head_without_body_or_redirects():
    network = next(p for p in load_probes() if p.id == "network_access")
    tree = ast.parse(network.source)
    connections = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute) and n.func.attr == "HTTPSConnection"]
    requests = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == "request"]
    assert len(connections) == len(requests) == 1
    assert ast.literal_eval(connections[0].args[0]) == "example.com"
    assert {k.arg: ast.literal_eval(k.value) for k in connections[0].keywords} == {"timeout": 2}
    assert [ast.literal_eval(arg) for arg in requests[0].args] == ["HEAD", "/"]
    assert not any(k.arg in {"body", "data"} for k in requests[0].keywords)
    assert not any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree))


def test_workload_sources_use_sleep_and_one_rate_limited_loop_without_host_execution():
    probes = {p.id: ast.parse(p.source) for p in load_probes()}
    output = probes["infinite_output"]
    loops = [n for n in ast.walk(output) if isinstance(n, ast.While)]
    assert len(loops) == 1
    sleeps = [n for n in ast.walk(loops[0]) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "sleep"]
    assert len(sleeps) == 1 and ast.literal_eval(sleeps[0].args[0]) == 0.005
    long = probes["long_running"]
    assert not any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(long))
    sleeps = [n for n in ast.walk(long) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "sleep"]
    assert len(sleeps) == 1 and ast.literal_eval(sleeps[0].args[0]) == 60


def test_fake_host_canary_is_not_embedded_in_remote_command_and_is_removed(monkeypatch):
    monkeypatch.setenv(HOST_CANARY_ENV, "previous-fake-value")
    with synthetic_host_canary() as path:
        fake = path.read_text()
        assert os.environ[HOST_CANARY_ENV] == fake
        assert fake.startswith("not-a-credential-host-canary-")
        for probe in load_probes()[1:]:
            command = build_probe_command(probe, path)
            assert fake not in command
        assert path.stat().st_mode & 0o777 == 0o600
    assert not path.exists()
    assert os.environ[HOST_CANARY_ENV] == "previous-fake-value"


class HostileModel:
    def __init__(self, path):
        self.path = path
        self.prompt = None

    async def complete_json(self, *, system, user, schema):
        self.prompt = json.loads(user)
        allowed = schema.model_json_schema()["$defs"]["EvidenceFileReplacement"]
        assert self.path not in allowed["properties"]["path"]["enum"]
        assert "untrusted" in system and "Preserve all existing tests" in system
        # Deliberately simulate a model obeying injected instructions despite the schema.
        return PatchProposal(replacements=[FileReplacement(
            path=self.path, lines=["def test_contract():", "    assert True"],
        )], summary="An injected assertion that must never become success")


class NeverSandbox:
    async def run(self, *args, **kwargs):
        raise AssertionError("Hostile model output must not reach any Sandbox execution")


@pytest.mark.parametrize("path", ["tests/test_contract.py", "../host.py", "src/unknown.py"])
async def test_prompt_injection_cannot_expand_edit_scope_or_mark_false_success(path):
    source = load_probes()[0].source
    evidence = RepositoryEvidence(
        repo_url="https://github.com/owner/fixture", dependency_manifests=["pyproject.toml"],
        python_files=["src/model.py", "tests/test_contract.py"], symbol_matches=[],
        baseline_summary="1 test passed",
        file_contents={
            "src/model.py": source, "tests/test_contract.py": "def test_contract(): pass\n",
            "pyproject.toml": '[project]\ndependencies = ["pydantic<2"]\n',
        },
    )
    strategy = MigrationStrategy(
        id="minimal", title="Minimal migration", rationale="Migrate the retained model",
        ordered_steps=["Preserve tests"], source_urls=["https://docs.pydantic.dev/latest/migration/"],
        target_files=["src/model.py", "pyproject.toml"],
    )
    model = HostileModel(path)
    result = await BranchRunner(model, NeverSandbox(), max_attempts=1).run(
        SandboxState("test-baseline-not-a-live-checkpoint"), strategy, evidence
    )
    assert result.status is BranchStatus.FAILED
    assert result.patch_applicable is False and result.checkpoint_id is None
    assert model.prompt["original_files"][0]["lines"] == source.splitlines()
    assert "Ignore previous instructions" in source


def completed(stdout="", stderr="", exit_code=0):
    return CommandResult(SandboxState("synthetic-test-child"), stdout, stderr, exit_code, 0.1)


@pytest.mark.parametrize("size, expected", [(32_000, True), (32_001, False)])
def test_recorded_output_bound_is_observed_not_assumed(size, expected):
    row = observation_from_result(load_probes()[4], completed("x" * size))
    assert row["captured_output_within_adapter_bound"] is expected
    assert row["stdout_bytes"] == size
    assert row["provider_timeout_enforced"] is None


def test_output_observation_counts_utf8_bytes_not_characters():
    row = observation_from_result(load_probes()[4], completed("中" * 11_000))
    assert row["stdout_bytes"] == 33_000
    assert row["captured_output_within_adapter_bound"] is False


def test_probe_alarm_is_not_misreported_as_provider_timeout():
    row = observation_from_result(load_probes()[5], completed(stderr=SAFETY_MARKER, exit_code=124))
    assert row["fixture_safety_ceiling_reached"] is True
    assert row["provider_timeout_enforced"] is None


def test_public_egress_and_missing_observations_never_claim_network_denial():
    probe = load_probes()[2]
    reached = observation_from_result(probe, completed(MARKER + json.dumps({
        "egress_observed": True, "http_status": 200,
    })))
    assert reached["observations"] == [{"egress_observed": True, "http_status": 200}]
    absent = observation_from_result(probe, completed("no structured observation"))
    assert absent["observations"] == []
    assert "network_blocked" not in json.dumps(absent)


def test_raw_response_secrets_and_arbitrary_string_values_are_not_retained():
    secret = "not-a-real-credential-MUST-NOT-EXPORT"
    raw = {"token": secret, "error_type": secret, "phase": secret, "http_status": secret}
    row = observation_from_result(load_probes()[1], completed(MARKER + json.dumps(raw), secret))
    assert secret not in json.dumps(row)
    assert row["observations"] == [{}]


class RecordingSandbox:
    def __init__(self):
        self.commands = []
        self.parent = SandboxState("synthetic-test-baseline")

    async def create_base(self, image, command):
        assert image == "reviewed-image"
        assert "not-a-credential-remote-canary" in command
        return self.parent

    async def run(self, parent, command, *, timeout_seconds):
        assert parent is self.parent
        assert timeout_seconds == 3
        self.commands.append(command)
        if len(self.commands) == 5:
            raise TimeoutError("not-a-real-credential-MUST-NOT-EXPORT")
        return completed(MARKER + json.dumps({"phase": "started"}))


async def test_probe_driver_only_sends_five_bounded_commands_to_remote_adapter(monkeypatch):
    def no_local_execution(*args, **kwargs):
        raise AssertionError("Fixture cannot be executed by a host process")

    monkeypatch.setattr("subprocess.run", no_local_execution)
    monkeypatch.setattr("os.system", no_local_execution)
    monkeypatch.setattr("asyncio.create_subprocess_exec", no_local_execution)
    sandbox = RecordingSandbox()
    report = await execute_probes(
        sandbox, image="reviewed-image", probes=load_probes(),
        host_canary_path=Path("/tmp/branchshift-security-test/host-only-canary.txt"),
    )
    assert len(sandbox.commands) == report["application_adapter_run_calls"] == 5
    assert report["model_calls"] == 0
    assert report["results"][-1]["error_type"] == "builtins.TimeoutError"
    assert report["results"][-1]["provider_timeout_enforced"] is None
    assert "not-a-real-credential-MUST-NOT-EXPORT" not in json.dumps(report)
    assert all("signal.alarm(8)" in command for command in sandbox.commands)
    assert ADAPTER_OUTPUT_LIMIT == 32_000
