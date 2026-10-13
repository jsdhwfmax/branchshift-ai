"""Inspect controlled fixture data; --execute explicitly runs five remote Sandbox probes.

No fixture is imported, evaluated or executed on the host. The default command
does not load application settings, credentials or providers.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import os
import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from app.providers.base import CommandResult, SandboxProvider

CASE_IDS = (
    "prompt_injection", "secret_discovery", "network_access", "host_path",
    "infinite_output", "long_running",
)
HOST_CANARY_ENV = "BRANCHSHIFT_HOST_ONLY_CANARY"
SAFETY_CEILING_SECONDS = 8
REQUEST_TIMEOUT_SECONDS = 3
ADAPTER_OUTPUT_LIMIT = 32_000
REMOTE_ROOT = "/workspace/branchshift-security"
MARKER = "__BRANCHSHIFT_SECURITY_OBSERVATION="
SAFETY_MARKER = "__BRANCHSHIFT_SAFETY_CEILING_REACHED"
DEFAULT_FIXTURES = Path(__file__).resolve().parents[4] / "evaluation/security"
ADAPTER_SOURCE = Path(__file__).resolve().parents[1] / "providers/contree.py"


@dataclass(frozen=True)
class Probe:
    id: str
    file: str
    mode: str
    source: str
    sha256: str


def load_probes(root: Path = DEFAULT_FIXTURES) -> list[Probe]:
    data = json.loads((root / "cases.json").read_text())
    if data.get("schema_version") != 1 or not isinstance(data.get("cases"), list):
        raise ValueError("Unsupported controlled security fixture manifest")
    rows = data["cases"]
    if [row.get("id") for row in rows] != list(CASE_IDS):
        raise ValueError("Security manifest must contain exactly the six reviewed cases in order")
    probes = []
    for row in rows:
        name = row["id"]
        expected = f"fixtures/{name}.py.txt"
        mode = "local_enforcement" if name == "prompt_injection" else "remote"
        timeout = None if mode == "local_enforcement" else REQUEST_TIMEOUT_SECONDS
        if row.get("file") != expected or row.get("mode") != mode:
            raise ValueError("Security fixture path/mode differs from reviewed scope")
        if row.get("timeout_seconds") != timeout:
            raise ValueError("Security fixture exceeds its reviewed timeout")
        path = root / expected
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Security fixture cannot resolve outside the fixture directory")
        raw = path.read_bytes()
        if len(raw) > 16_000:
            raise ValueError("Security fixture exceeds its source limit")
        source = raw.decode("utf-8")
        ast.parse(source, filename=expected)  # Parse as data; NEVER exec/import these fixtures.
        probes.append(Probe(name, expected, mode, source, hashlib.sha256(raw).hexdigest()))
    return probes


def runtime_metadata() -> dict[str, Any]:
    """Fingerprint code and installed package metadata without importing a provider."""
    try:
        sdk_version = version("contree-sdk")
    except PackageNotFoundError:
        sdk_version = None
    return {
        "sdk_distribution": "contree-sdk",
        "sdk_version": sdk_version,
        "adapter_source_sha256": hashlib.sha256(ADAPTER_SOURCE.read_bytes()).hexdigest(),
        "probe_runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def inspection_report(probes: list[Probe]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "evidence_scope": "static fixture inspection; no model or Sandbox calls",
        "remote_execution": "not_performed",
        "remote_run_calls_planned": 5,
        "baseline_calls_planned": 1,
        "model_calls_planned": 0,
        **runtime_metadata(),
        "provider_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "fixture_alarm_seconds": SAFETY_CEILING_SECONDS,
        "network_scope": "one HTTPS HEAD to example.com/; no redirects or credentials",
        "cases": [{"id": p.id, "mode": p.mode, "file": p.file, "sha256": p.sha256}
                  for p in probes],
    }


def baseline_command() -> str:
    # Deliberately creates only two public synthetic files inside the remote filesystem.
    return (
        "python - <<'BRANCHSHIFT_SECURITY_SETUP'\n"
        "from pathlib import Path\n"
        f"root = Path({REMOTE_ROOT!r})\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        "(root / 'remote-only-marker').write_text('controlled-security-probe')\n"
        "(root / 'fake-secret.txt').write_text('not-a-credential-remote-canary')\n"
        "BRANCHSHIFT_SECURITY_SETUP"
    )


def build_probe_command(probe: Probe, host_canary_path: Path) -> str:
    if probe.mode != "remote" or probe.id not in CASE_IDS[1:]:
        raise ValueError("Prompt injection is tested at the application boundary, not executed")
    path = PurePosixPath(str(host_canary_path))
    if (
        not path.is_absolute() or ".." in path.parts or path.name != "host-only-canary.txt"
        or path.parent.parent != PurePosixPath("/tmp")
        or not path.parent.name.startswith("branchshift-security-")
    ):
        raise ValueError("Host-path probe accepts only the fresh synthetic /tmp canary location")
    # The host transmits a fake filename, never the host canary value or host environment.
    header = (
        "import json, os, signal, sys\n"
        "from pathlib import Path\n"
        f"marker = Path({REMOTE_ROOT + '/remote-only-marker'!r})\n"
        "if marker.read_text() != 'controlled-security-probe':\n"
        "    raise SystemExit('Remote security-probe marker missing')\n"
        f"HOST_CANARY_PATH = {str(path)!r}\n"
        "def emit(observation):\n"
        f"    print({MARKER!r} + json.dumps(observation), flush=True)\n"
        "def safety_stop(signum, frame):\n"
        f"    print({SAFETY_MARKER!r}, file=sys.stderr, flush=True)\n"
        "    raise SystemExit(124)\n"
        "signal.signal(signal.SIGALRM, safety_stop)\n"
        f"signal.alarm({SAFETY_CEILING_SECONDS})\n"
    )
    return "python -u - <<'BRANCHSHIFT_REMOTE_PROBE'\n" + header + probe.source + (
        "\nBRANCHSHIFT_REMOTE_PROBE"
    )


@contextmanager
def synthetic_host_canary() -> Iterator[Path]:
    """Create only our own ephemeral fake host file/env value, then restore/remove them."""
    previous = os.environ.get(HOST_CANARY_ENV)
    value = "not-a-credential-host-canary-" + secrets.token_hex(16)
    with TemporaryDirectory(prefix="branchshift-security-", dir="/tmp") as directory:
        path = Path(directory) / "host-only-canary.txt"
        path.write_text(value)
        path.chmod(0o600)
        os.environ[HOST_CANARY_ENV] = value
        try:
            yield path
        finally:
            if previous is None:
                os.environ.pop(HOST_CANARY_ENV, None)
            else:
                os.environ[HOST_CANARY_ENV] = previous


def observation_from_result(probe: Probe, result: CommandResult) -> dict[str, Any]:
    observations = []
    for line in result.stdout.splitlines():
        if line.startswith(MARKER):
            try:
                item = json.loads(line[len(MARKER):])
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                observations.append(item)
    # Retain only reviewed Boolean/count/status fields, never arbitrary returned values.
    booleans = {
        "remote_fake_canary_readable", "host_fake_env_visible", "host_fake_file_readable",
        "egress_observed",
    }
    words = {
        "phase": {"started", "completed"},
        "observation": {"not_found", "permission_denied", "readable"},
        "workload": {"infinite_output", "long_running"},
        "error_type": {
            "SSLError", "SSLCertVerificationError", "TimeoutError", "ConnectionResetError",
            "ConnectionRefusedError", "gaierror", "RemoteDisconnected", "BadStatusLine",
            "InvalidURL", "IncompleteRead", "HTTPException", "OSError",
        },
    }
    facts: list[dict[str, Any]] = []
    for row in observations[:4]:
        fact: dict[str, Any] = {}
        for key, value in row.items():
            if (
                (key in booleans and (type(value) is bool or value is None))
                or (key in words and isinstance(value, str) and value in words[key])
                or (key == "http_status" and type(value) is int and 100 <= value <= 599)
                or (key == "requested_sleep_seconds" and type(value) is int and value == 60)
            ):
                fact[key] = value
        facts.append(fact)
    stdout_bytes = len(result.stdout.encode("utf-8"))
    stderr_bytes = len(result.stderr.encode("utf-8"))
    safety_ceiling = SAFETY_MARKER in result.stderr
    completed_workload = any(row.get("phase") == "completed" for row in facts)
    return {
        "case_id": probe.id, "fixture_sha256": probe.sha256,
        "provider_returned_result": True, "checkpoint_id": result.state.checkpoint_id,
        "exit_code": result.exit_code, "elapsed_seconds": result.elapsed_seconds,
        "stdout_bytes": stdout_bytes, "stderr_bytes": stderr_bytes,
        "captured_output_within_adapter_bound": (
            stdout_bytes <= ADAPTER_OUTPUT_LIMIT and stderr_bytes <= ADAPTER_OUTPUT_LIMIT
        ),
        "output_limit_reached": stdout_bytes >= ADAPTER_OUTPUT_LIMIT,
        "fixture_safety_ceiling_reached": safety_ceiling,
        "long_workload_completed": completed_workload,
        "observations": facts,
        "provider_timeout_enforced": None,
        "note": (
            "A bounded response/nonzero exit alone does not prove provider timeout enforcement. "
            "The independent fixture alarm is a probe safety mechanism, not an application limit."
        ),
    }


async def execute_probes(
    sandbox: SandboxProvider, *, image: str, probes: list[Probe], host_canary_path: Path
) -> dict[str, Any]:
    """Only the supplied remote adapter receives command strings; no local shell exists here."""
    started = time.monotonic()
    metadata = runtime_metadata()  # Capture source before any remote calls, not afterward.
    baseline = await asyncio.wait_for(sandbox.create_base(image, baseline_command()), timeout=45)
    rows = []
    for probe in probes:
        if probe.mode != "remote":
            continue
        call_started = time.monotonic()
        try:
            result = await asyncio.wait_for(sandbox.run(
                baseline, build_probe_command(probe, host_canary_path),
                timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            ), timeout=20)
            rows.append(observation_from_result(probe, result))
        except Exception as exc:
            # Exception text may contain auth or response content; store only its type.
            operation_id = None
            with suppress(ValueError):
                operation_id = str(UUID(str(getattr(exc, "operation_uuid", ""))))
            rows.append({
                "case_id": probe.id, "fixture_sha256": probe.sha256,
                "provider_returned_result": False,
                "error_type": type(exc).__module__ + "." + type(exc).__qualname__,
                "operation_id": operation_id,
                "elapsed_seconds": round(time.monotonic() - call_started, 3),
                "provider_timeout_enforced": None,
                "note": (
                    "Error/timeout observed; remote termination was not independently verified."
                ),
            })
    return {
        "schema_version": 1, "evidence_scope": "controlled remote Sandbox probe observations",
        **metadata,
        "image": image, "baseline_checkpoint_id": baseline.checkpoint_id,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "model_calls": 0, "application_adapter_baseline_calls": 1,
        "application_adapter_run_calls": len(rows),
        "call_count_scope": "adapter invocations, not total SDK HTTP calls or billable operations",
        "prompt_injection": "separate local enforcement tests; no live model resistance claim",
        "provider_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "fixture_alarm_seconds": SAFETY_CEILING_SECONDS,
        "host_canary": "fresh synthetic file and environment variable; values never exported",
        "results": rows,
        "limitations": [
            "No complete host-filesystem, credential-discovery or network-denial claim.",
            "Public HEAD success demonstrates allowed egress; failure does not prove denial.",
            "CPU and memory limits are not configured or tested by this adapter.",
            "No automatic retry, image publication, target-repository execution or model calls.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--execute", action="store_true", help="Explicitly call real Sandbox APIs")
    parser.add_argument("--output", type=Path, help="New JSON evidence path; never overwrite")
    args = parser.parse_args()
    probes = load_probes(args.fixtures)
    if not args.execute:
        print(json.dumps(inspection_report(probes), indent=2))
        return
    if args.output is None or args.output.exists():
        parser.error("--execute requires a new --output path")
    # Credentials and provider initialization are unreachable in the default inspection mode.
    from app.config import settings
    from app.providers.contree import ContreeSandboxProvider

    async def run() -> dict[str, Any]:
        with synthetic_host_canary() as path:
            async with ContreeSandboxProvider(
                settings.nebius_api_key, settings.nebius_project_id, settings.contree_api_url
            ) as sandbox:
                return await execute_probes(
                    sandbox, image=settings.contree_image, probes=probes, host_canary_path=path
                )

    failed = False
    try:
        report = asyncio.run(run())
    except Exception as exc:
        failed = True
        report = {
            "schema_version": 1,
            "evidence_scope": "remote probe collection incomplete",
            "error_type": type(exc).__module__ + "." + type(exc).__qualname__,
            "inspection": inspection_report(probes),
            "note": "No complete remote evidence; initialization/preparation may have failed.",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(f"EVIDENCE={args.output.resolve()}")
    print("Observations retained; exit zero does not declare all isolation properties proven.")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
