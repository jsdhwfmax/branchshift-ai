# BranchShift — product feedback draft

**Prepared feedback, 10 September 2026. Not sent.** The
[plain-text submission copy](feedback-for-devpost.txt) is ready for the feedback
field, subject to the actual form's length limit and any later findings from
the submitted release. These notes supply its evidence and distinguish provider
friction from BranchShift implementation work. No Cloud-hosting experience is
claimed. Keep project/account identifiers private unless support needs them
through an authorized channel.

## 1. Make Sandbox Beta permissions visible beside inference access

**Observed.** On 31 August, the credentialed Sandbox spike reached the service,
but the permission response reported `spawn=false`, `spawn_disposable=false`
and `list=false`; the first spawn returned HTTP 403. Sandbox Beta access
required a separate request. After the welcome email, a real three-branch
spike passed on 10 September.

**Impact.** Having an API key was insufficient to establish readiness for
Sandbox workflows. It was easy to confuse account/inference setup with Sandbox
permission. This delayed our branching verification. We have not measured the
provider's approval-processing time, so the dates should not be presented as a
service-level timing claim.

**Suggestion.** Show a Sandbox readiness panel with current project, approved
capabilities and a direct Beta-request/status link. Return an actionable error
for a valid key lacking Sandbox permissions, distinguishing that condition from
an invalid token or missing project identifier. Include a documented minimal
permission check before the first spawn.

**Evidence.** [Sandbox spike and earlier denied attempt](../evidence/sandbox-spike.md).
The access issue is now resolved for the configured project.

## 2. Match the SDK quickstart to an installable version

**Observed.** Documentation examples reviewed on 31 August used
`ContreeAsyncClient` transport injection. The verified
`contree-sdk==0.4.0.dev5` environment used for the successful 10 September spike
constructs `Contree(ContreeConfig(auth=IAMAuth(token=..., project_id=...)))`.
BranchShift's adapter is pinned to that verified surface; it does not claim
compatibility with untested alternate constructors.

**Impact.** A developer following the documented constructor could encounter an
API-surface mismatch with the package they installed. Our adapter keeps that
version difference out of the orchestrator, but it adds integration work.

**Suggestion.** Put an exact installation command and version badge beside
every SDK quickstart. Test the example against the released artifact in CI;
separate unreleased examples from stable/prerelease examples. Add an upgrade
note showing the old and new constructors and required IAM/project inputs.

**Evidence.** [Provider interface audit](../evidence/provider-interface-audit.md)
and [successful pinned-SDK spike](../evidence/sandbox-spike.md).
This is a dated observation; recheck before stating that the current published
documentation still has the mismatch.

## 3. Shared filesystem states fit comparative agent workflows

**Observed.** A real baseline and three child states produced the expected
isolated marker output. The complete small spike took 4.581 seconds.

**What helped.** Stable state identifiers give us a concrete way to express
competing attempts from a common parent and preserve their individual outputs.
That is the central infrastructure primitive for BranchShift's implemented
migration comparison. The separate completed evaluation retained 15 real
baseline/winner-revalidation records across five migration cases.

**Suggestion.** A maintained example that shows a prepared Python environment,
three independent patches, structured test reports and clean-baseline winner
reapplication would help developers carry the primitive into a complete agent
workflow. Include child-state lifecycle and cleanup guidance.

**Limit.** The marker result measures neither repository migration latency nor
cost-effectiveness. The later five-case series measures end-to-end ledger
duration and reported-token cost separately: median 53.022 seconds, p95
114.892 seconds and USD 0.654327 estimated inference across all 15 runs.
These are small-fixture observations, not evidence of comparative cost savings,
an invoice or a general latency guarantee. See the
[complete cohort](../../evaluation/series-20260910/README.md).

## 4. NVIDIA model and migration outcomes

**Observed.** Three predeclared rounds of validators, configuration,
serialization, parsing and compatibility finished at frozen revision
`92c733a`. All 15 runs yielded a qualified native-Pydantic-2 migration after
clean-baseline revalidation. The 45 candidate results include 38 passes and
seven failures. The exact model was `nvidia/Nemotron-3-Ultra-550b-a55b`, with
thinking enabled. All 79 model requests returned complete token-usage fields.
These are whole-pipeline outcomes with bounded repair loops, not a per-response
model accuracy or structured-output success rate.

A separate UI-started run at `63cf7fd`, `3ddea183879b`, retained two passing
candidates and one failure. Minimal and compatibility passed 13 tests with one
lint finding each; minimal won with 44 changed lines versus 71. Its exact patch
passed the original tests again from a distinct clean checkpoint. The failed
refactor retained 11/13 tests. See the
[release record](../evidence/runtime-release-63cf7fd/README.md).

**What helped.** Grounded model-generated alternatives gave the evaluator
concrete patches to compare. A plausible candidate could fail while another
preserved behavior. Keeping citations, started attempts and diagnostics made
that outcome inspectable. The data do not establish that three strategies beat
one under a matched budget; that comparison has not been run.

**Suggestion.** Provide a versioned Nemotron coding example that combines exact
model identity, thinking and structured-output settings with executable tests,
bounded repairs and complete usage accounting. Show rejected outputs and
application checks alongside successful responses.

**Ownership.** Treat these as BranchShift defects or incomplete validation until
a provider-specific failure is reproduced in a minimal independent example.
Do not blame Nebius or NVIDIA for orchestration or evaluator mistakes.

The earlier 16 development attempts remain a separate record across changing
code and model settings. They are not pooled into the frozen series. Five
small authored cases do not establish general production migration reliability.

## 5. Distinguish client waiting from remote workload termination

**Observed.** Two controlled remote fixtures produced SDK
`OperationTimedOutError` exceptions. Subsequent read-only status checks on the
same operation handles reported terminal operation `SUCCESS`, while process
results reported `timed_out=true`, signal 9 and exit -1. The infinite-output
case also reported 32,000 captured stdout bytes and `truncated=true`.

**Impact.** An exception alone did not distinguish the client wait deadline
from confirmed provider-reported workload timeout. Operation-level `SUCCESS`
also needed interpretation alongside the process result. We retained the
handles and queried their state instead of repeating uncertain executions.

**Suggestion.** Expose separate typed outcomes for client wait expiry and remote
process timeout, and include the operation handle, terminal process status and
output-truncation status in one documented recovery example. Document billable
operation units separately from SDK invocations and polling.

**Evidence and limit.** [Controlled probes and terminal status receipts](../evidence/security-boundaries.md).
This is provider telemetry for two bounded fixtures, not an independent
OS-level proof that no process survived. Public egress was allowed in the
separate network check; no CPU, memory or egress-denial guarantee is asserted.

## Collected feedback evidence and limits

| Area | Evidence available and remaining limit |
| --- | --- |
| NVIDIA model quality | Exact model/settings, 45 candidate outcomes and all 15 qualified winners retained; small authored fixtures only |
| Structured output | Validated retained plans/patches and bounded repair behavior; no separately established all-response schema success rate |
| End-to-end latency and usage | 15 ledger durations, 79 requests, 275,634 input and 126,231 output tokens; USD 0.654327 reported-token estimate with rate card, excluding other services and taxes |
| Sandbox workflow | 176 returned adapter calls in the cohort, distinct states and clean revalidation; two separate timeout-status receipts. Adapter calls are not billed operation counts |
| AI Cloud hosting | No actual deployment yet; no hosting feedback is included in the prepared submission copy |

The prepared feedback covers the services actually exercised. Add Cloud
observations only after hosted verification; do not fill that gap with a
proposed deployment or treat BranchShift defects as reproduced provider bugs.
