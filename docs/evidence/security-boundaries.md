# Controlled security-boundary verification

Updated 10 September 2026. One real Sandbox baseline and five controlled remote
probes completed collection in **16.080 seconds**, with no model calls. Three
probes returned observations; two raised SDK timeout exceptions. Two subsequent
read-only status requests confirmed terminal operations with provider-reported
timeout termination. This document separates those observations, local
application checks, and properties that remain unverified. It does not claim
complete isolation or general prompt-injection immunity.

The [original probe report](../../evaluation/security/evidence/probes-20260910.json)
is copied byte-for-byte from the private execution artifact (SHA256
`c93a535b21edcf6598d0707859a79014c82d47a962f26f55fc2112371eeac764`).
The separate [status receipt](../../evaluation/security/evidence/operation-status-20260910.json)
records the two existing operation handles queried at 05:51:34 UTC. No probe
was rerun. Both artifacts omit credentials, arbitrary stdout/stderr and raw
exception messages. The original report's unknown timeout fields are retained;
the later service response is additional evidence, not a rewrite of history.

## Local evidence and exact scope

[Six controlled fixtures](../../evaluation/security/cases.json) cover the
categories in the [implementation plan](../superpowers/plans/2026-08-31-branchshift-implementation.md).
They are `.py.txt` data, never host-executed modules. The
[local tests](../../services/api/tests/security/test_untrusted_repositories.py)
parse and inspect their source, exercise application validation using hostile
model substitutes, and exercise the probe driver using a recording fake
Sandbox. No synthetic result from those tests is placed in the live evidence
or migration-attempt manifest.

The focused local suite passed **26 tests** using the cached Python runtime
with pytest plugin autoload disabled and `pytest_asyncio` explicitly enabled.
Ruff passed for the new CLI and tests; mypy passed for the new CLI. This verifies
the listed local structure/enforcement behavior, independently of remote
observations. The checks also confirm default CLI inspection does not import settings
or providers, unknown output fields are omitted, and fake host canaries are
removed/restored after use.

| Boundary | Local evidence | Actual remote observation and limit |
| --- | --- | --- |
| Repository prompt injection | An injected comment asks for test edits, extra paths and fake host information. A deliberately hostile model response cannot expand the editor path enum or change protected tests; the real application reports failure before execution | No real-model resistance rate has been measured; approved source changes still execute as untrusted code in the Sandbox |
| Secret discovery | Static checks permit only one fake remote file and one dedicated fake host environment variable; command construction never includes the host canary value | Exit 0: remote fake file readable; fake host variable absent. This establishes only the selected canary boundary, not protection from every credential-discovery technique |
| Network access | Exactly one public, credential-free HEAD request, no redirect/retry/body or loop | Exit 0: `example.com` returned HTTP 200. Public egress is allowed; this is not an egress-denial result |
| Host path | Command builder refuses locations other than its own fresh `/tmp` fake file; no host mounts, directory scans or credential paths are requested | Exit 0: selected host file not found remotely. This is not an exhaustive filesystem-isolation proof |
| Infinite output | The only output loop sleeps between writes; the wrapper installs an eight-second safety alarm first | SDK timeout after 4.351 s; status response reports terminal operation, process `timed_out=true`, signal 9, duration 3.334 s, and exactly 32,000 captured stdout bytes with `truncated=true`. This verifies the service's reported truncation and timeout for this fixture, not an unlimited-producer or OS-level isolation guarantee |
| Long-running process | One sleeping process, no forks or busy loop, bounded provider request plus independent alarm | SDK timeout after 4.585 s; status response reports terminal operation, process `timed_out=true`, signal 9 and duration 3.312 s. No independent OS-level process-survival inspection was performed |

## Timeout receipt interpretation

The baseline checkpoint is `9f5152fc-a696-4ba3-b717-b82bfc2e9edc`.
The timeout operation IDs are:

- Infinite output: `01a089dc-e1fe-73ec-85f6-0d52f35a3e4c`.
- Long running: `01a089dc-f2ff-7747-abed-d07bb9ce5a83`.

For each existing handle, `get_operation_status(..., inflight=False)` returned
operation status `SUCCESS`, requested timeout 3 seconds, process exit code -1,
signal 9 and `timed_out=true`. Here `SUCCESS` describes the completed operation
record; it does **not** mean the workload exited normally. The infinite-output
response additionally reported ASCII stdout truncated to 32,000 bytes. The
long-running response reported 115 stdout bytes without truncation. Both
reported zero stderr bytes, so the report does not attribute termination to
the fixture's eight-second alarm.

Inspection of installed `contree-sdk==0.4.0.dev5` explains why its exception
alone was insufficient: `_internals/io/operation_waiter.py`,
`OperationWaiter.wait_for_result`, raises `OperationTimedOutError` both for a
client wait deadline and for a received process exit event with `timed_out`.
The generated API model `InstanceResultState.timed_out` describes a process
killed when the operation timeout is reached. The later status receipt
therefore supports **provider-reported timeout termination** and a terminal
server record for these two executions. It remains provider telemetry, not an
independent OS-level demonstration that no process survived.

## Inspected limits and missing guarantees

The installed `contree-sdk==0.4.0.dev5` image-like `run` interface supports
`timeout`, `truncate_output_at`, `env`, `files`, and `preserve_env`. In the
inspected implementation, `env` and `files` default to empty collections and
`preserve_env` defaults to false. The
[BranchShift adapter](../../services/api/app/providers/contree.py) passes its
execution timeout and a 32,000-byte truncation bound; it does not pass host
environment variables or mount host files into the spawned process. Its
authentication remains on the API client side. The canary probes check
the observed boundary rather than infer complete isolation from this
API shape. Each report records the actual installed SDK distribution version
and SHA256 of the adapter source captured before remote calls, alongside the
driver and fixture hashes. These fingerprints read no environment credentials.

The SDK truncation setting is expressed in bytes. The inspected adapter
redacts the returned strings and does not add a character-count slice. The
probe report measures the resulting text as UTF-8 bytes; its infinite-output
fixture uses ASCII, where character and byte counts coincide. A local
multibyte-text test also verifies that the report does not confuse these units.

This adapter exposes no per-call CPU, memory or egress controls. Those resource
or policy guarantees are **not established** by the local tests. Public
dependency installation already needs network access; the network probe must
not label working egress a security-test failure or pretend it was blocked.
The probe's eight-second alarm and output pacing are experimental safeguards,
not protections supplied to arbitrary repository code by the application.

SDK output limits bound collected output, not necessarily bytes produced
inside a process. A client wait deadline does not prove remote cancellation.
The initial report therefore leaves `provider_timeout_enforced` unknown and
records observable exits, SDK exception type/operation ID when available, and
whether the fixture's own alarm fired. The separate status receipt strengthens
the evidence for the two timed-out operations as described above. No missing
observation becomes a successful gate.

SDK operation cost units have not been established. These probes make **no
claim of dollar/credit cost**, and adapter invocation counts must not be
substituted for complete SDK HTTP requests or billed operation counts.

## Collection scope and remaining limits

The [probe driver](../../services/api/app/cli/security_probes.py) defaults to
static inspection. Explicit `--execute` is required to initialize the real
provider. The [fixture README](../../evaluation/security/README.md) describes
the one-baseline/five-run experiment, fixed harmless destination, fake canary
handling and separate output artifact. No model calls, target-repository
execution, publication or deployment are included.

The completed experiment used one baseline-adapter call and five run-adapter
calls; the follow-up made two read-only status requests and no new execution
requests. These counts do not describe the SDK's complete HTTP traffic or
billable operations. Prompt injection remains a deterministic application
boundary test with a hostile model substitute, not a measured real-model
immunity rate. CPU/memory enforcement, complete host isolation, network denial
and independent OS-level termination are not established by this evidence.
Application changes for public admission, per-user quotas or other resource
controls require separate runtime evidence.
