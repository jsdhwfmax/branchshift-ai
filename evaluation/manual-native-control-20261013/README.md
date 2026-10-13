# Manual reference migration: feasible within the existing limits

A reference patch authored directly with Codex passed the original `pydantic-yaml`
suite on native Pydantic 2.12.5, then passed again on a fresh checkout and runtime.
Both executions retained **14 passed tests and one historical xfail**, with a
successful dependency check, unchanged test/configuration contract, and native
`pydantic.BaseModel` inheritance. This establishes feasibility on this one inspected
case. **It is not a BranchShift/Nemotron autonomous migration success.**

There were zero additional evaluated Nebius/Nemotron API calls. Codex authorship is
AI assistance; the machine field `model_calls: 0` explicitly counts only the evaluated
Nebius provider. The earlier 15 provider requests and their failures remain unchanged.

## What the comparison establishes

| Method / condition | Observed result | Interpretation |
| --- | --- | --- |
| Original project, Pydantic 1.10.24 | 14 passed, 1 historical xfail | Qualified original baseline |
| Official `bump-pydantic` at its frozen commit | 8 collection errors; repeated on a clean copy | Codemod alone did not complete this migration |
| Earlier BranchShift development iterations, 15 real Nemotron requests | No patch reached runtime validation | Generation failure; not a completed suite with “0/15 tests passing” |
| Codex-assisted manual reference, this control | 14 passed, 1 xfail; same result on a fresh copy | A valid solution fits the current protocol, but autonomous reliability remains unproven |

Baseline, codemod, and original model evidence are retained in the separate
[external comparison](../external-pydantic-yaml/README.md). These are development
observations on one case, not independent success-rate samples or a single-agent ablation.

## Fixed conditions and actual runs

- Upstream: `NowanIlfideme/pydantic-yaml` v0.11.2, commit
  `54ff4bad7bca758a9dd22a791b707a2b9c27159e`; its MIT license is in
  [frozen/upstream-LICENSE](frozen/upstream-LICENSE).
- Ubuntu 24.04, Python **3.12.15**, Pydantic **2.12.5**, and the complete same
  [dependency constraints](frozen/candidate-environment/constraints.txt) as the codemod.
  Python 3.12 is the previously disclosed adaptation from this older upstream project.
- Full original `src/pydantic_yaml/test` suite and configuration; no test edits,
  new skips, omitted original passing tests, or `pydantic.v1` compatibility shim.
- Standard GitHub-hosted runners, no user secrets or persisted checkout credentials,
  no dependency cache. This is **not** Nebius Sandbox/checkpoint evidence.

| Execution | Source / run | Qualification |
| --- | --- | --- |
| Candidate, manual iteration 1 | `8959a9a`; [run 38337450261](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38337450261) | [summary](run-38337450261/evidence/summary.json), [exact application checks](run-38337450261/evidence/validation/application-check.json) |
| Fresh clean repeat, same iteration | `0d22c5f`; [run 38337713201](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38337713201) | [summary](run-38337713201/evidence/summary.json), [exact application checks](run-38337713201/evidence/validation/application-check.json) |

The original application command and the separate comparator suite both passed in
each run. The full runtime lock and expected source tree were unchanged after execution.
The patch SHA-256 was identical in both runs:
`c1d9c8d185177a3d78a55a2fd20c213bbf3c424471e2cdf90930d6900a8582be`.
The command SHA-256 was identical:
`05c24cf6ff0eda89737a7ae70ba531e0c38b821b0f77034c93d7821013271566`.
Applied Git tree: `8e7e79e44383d605e33e36041e3c779e5d853467`.

One candidate and one clean repeat were used. The other three permitted manual
iterations were not executed. The [execution ledger](execution-ledger.json) is closed.
Raw logs, JUnit, outcomes, source inventories, environment locks, receipts, patch,
and command are retained under both run directories, beyond GitHub's one-day artifact retention.

## The existing edit limits were sufficient

The actual production `evidence_patch_schema` and `proposal_to_patch` accepted the
[reference edit proposal](inputs/candidate-01/edit-proposal.json):

| Limit | Actual | Existing maximum |
| --- | ---: | ---: |
| Source edits | 14 | 40 |
| New lines in a single edit | 35 | 120 |
| Total new lines, including retained context | 210 | 600 |
| Total new UTF-8 bytes, counting line endings | 7,491 | 24,000 |

The manifest was changed only by the existing deterministic Pydantic dependency
upgrade. Three source files were edited: YAML parsing/dumping, native SemVer
schema handling, and versioned-model validation. The emitted patch was replayed
against the exact original source and compared with the manually edited copy.
See the [production protocol receipt](inputs/candidate-01/protocol-receipt.json)
and [manual source integrity checks](manual-source-static-receipt.json).

## Product regression checks

The new dataset-driven regression file replays eight complete retained failed
candidate responses, verifies zero executor calls, and preserves the distinction
between rejected proposals and tests that actually ran. It also covers the repeated
33 identical edits, 705/834-line outputs, incomplete 120-line replacement, forbidden
plan path, and legacy-protocol isolation. Existing mocked bounded length-retry tests
remain in place. No historical model response was edited.

Product commit `d7efab1` passed [CI run 38336750286](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38336750286):
555 API, 13 fixture, 88 web, and 12 browser checks; lint, types, and build passed.
The focused offline group passed 86 checks, including 16 new cases. The isolated
manual harness passed 23 local checks without running upstream code on the host.
The [offline receipt](offline-regression-receipt.json) records the evidence anchors.

After the manual control, product commit `ab98a73` aligned the planner with the
editor's unchanged limits. A shared constants module now supplies the schema,
validation, initial prompt, and repair messages. Planning explicitly accounts for
local edits and the deterministic manifest upgrade without receiving any manual
reference code or case-specific file selection. Focused offline checks passed 165
tests plus lint/types. The [alignment replay receipt](alignment-replay-receipt.json)
confirms that the manual input still generates the exact previously executed patch
and validation command. The new planner prompt has not yet been evaluated with a
real provider request; no new autonomous success is claimed.
The final implementation passed [CI run 38338534313](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38338534313):
**558 API, 13 fixture, 88 web, and 12 browser checks**, plus lint, types, and build.
This phase publishes source and evaluation evidence; it does not deploy the new
planner prompt to Render or change the live judge allowance.

## Limits and next decision

Passing these tests does not establish full behavior preservation. One original
test has no assertions; one known round-trip behavior remains xfailed. Source lint
still reports 49 findings (original baseline: 51); lint was recorded, not silently
made a new migration pass criterion. Only one external project was examined.

This case has now been inspected and manually solved, so later retries are development
retests, not held-out evaluation. Do not provide this reference patch to the evaluated
model and then count the result as autonomous success. A later reliability or branching
advantage claim requires separate prospective evidence.

The model-call budget for this phase remains zero. Actual total-budget headroom
has not been reconciled, so no new paid retest was started. The next experiment must
be separately frozen and bounded before it runs. No competition submission or video
publication occurred. The [proposed three-call retest](NEXT-RETEST.md) is not executed.
Harness mechanics are documented in [HARNESS.md](HARNESS.md).
