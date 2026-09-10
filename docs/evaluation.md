# Pydantic migration evaluation

Updated 10 September 2026. The separate
[predeclared three-round cohort](../evaluation/series-20260910/README.md)
completed **15/15 qualified live migrations**, all five cases attempted three
times against frozen baseline/runtime `92c733a`. Its median ledger duration is
53.022 seconds; p95 114.892 seconds. Versioned collection records 79 model
requests with complete returned usage and 176 Sandbox adapter SDK calls.
The response-token inference estimate is USD 0.654327, excluding other services
and taxes. That small controlled cohort has its own plan, manifest, raw exports
and failures at candidate level; it is not a general reliability claim.

The sections below describe the **earlier 16-attempt development cohort**:
9 failures and 7 qualified successes while code/model settings changed.
Its original aggregate remains unchanged, and none of its partial-case counts
should be mistaken for the newer complete series. Aggregation reads retained
exports and calls no providers.

## Recorded attempts and the three-run streak

The [generated results](../evaluation/results.md) and
[machine-readable aggregate](../evaluation/results.json) retain all 16
attempts, including the nine failures while code and model settings changed.
There is no fixed-configuration 16-trial success-rate claim.

| Run | Winner | Preserved tests and clean revalidation | Ledger duration |
| --- | --- | --- | ---: |
| [6d863a18d814](../evaluation/evidence/6d863a18d814.json) | compatibility | 13/13 passed under Pydantic 2 | 89.343 s |
| [83489c0de0de](../evaluation/evidence/83489c0de0de.json) | compatibility | 13/13 passed under Pydantic 2 | 77.417 s |
| [aedb7bf272f4](../evaluation/evidence/aedb7bf272f4.json) | minimal | 13/13 passed under Pydantic 2 | 89.912 s |

These are the final three chronological attempts on the validators case, with identical baseline
commit, project path, NVIDIA model, orchestrator digest and runtime-config
digest. The recorded dirty checkout is disclosed. The aggregate's
`three_consecutive_pass` is true; `independent_cases_with_success` is **5** and
`five_cases_pass` is true. `three_successes_per_case` remains false.

The four additional cases ran against public baseline commit
`b8a1204ceaec260261c8fe1d695eae23c4597ae8`. All four qualified winners and their
clean-baseline revalidations passed the original test contracts under Pydantic 2.
The config run was created through the API/UI; the other three used the CLI.

| Case / run | Winner | Preserved tests and clean revalidation | Failed candidate retained | Ledger duration |
| --- | --- | --- | --- | ---: |
| [config / 113e13ad8413](../evaluation/evidence/113e13ad8413.json) | refactor | 5/5 passed | compatibility | 59.695 s |
| [serialization / 714229fb2814](../evaluation/evidence/714229fb2814.json) | compatibility | 4/4 passed | minimal | 48.199 s |
| [parsing / 5b124a9d5dee](../evaluation/evidence/5b124a9d5dee.json) | minimal | 4/4 passed | none | 49.323 s |
| [compatibility / fe86c430aa32](../evaluation/evidence/fe86c430aa32.json) | minimal | 4/4 passed | none | 57.627 s |

The serialization minimal candidate failed patch safety validation after
three attempts, with invalid Python syntax recorded; it has no child checkpoint
ID. Its two successful candidates and the clean winner revalidation do have
recorded checkpoints. Thus six of the seven qualified runs record three
distinct candidate child IDs; serialization proves a verified winning
migration, not three executed child states. The aggregate keeps this separate
from the winner's success gates.

The config run was also inspected in the local browser after refresh: it
remained completed with refactor, 5/5 tests, baseline `b8a1204` and its clean
revalidation checkpoint. Its same-origin API report's `run` object matched
the original summary. The downloaded patch matched the retained patch byte
for byte: **1,061 bytes**, SHA256
`7ce158457e4af8b80a16aef415c902a90957477314c920739875f5ce9e43f4f2`.
This establishes the local refresh/report/download path, not public hosting.

All seven successes record the same orchestrator content digest and runtime
configuration digest. The long-lived config API process records orchestrator
revision `afb82d4`, while the other three new CLI records identify `b8a1204`;
their content digests agree. These original provenance fields are preserved,
including dirty-checkout disclosures. The new cases have a different baseline
commit/path from the validators series and do not extend its repetition count.

Run **`6d863a18d814`**, inspected on 10 September, is a completed live migration
of the original 13-test fixture at baseline commit
`afb82d4fdeace940e0054895c73a0ddca2ff55c3`, using
`nvidia/Nemotron-3-Ultra-550b-a55b`. The retained record passes the aggregator's
evidence gates. The minimal branch failed; compatibility and refactor each
passed 13/13 tests under Pydantic 2 with preserved test contracts. Compatibility
won with one lint finding versus refactor's two, then passed 13/13 again during
clean-baseline revalidation. This selection is not a smallest-patch claim.

Its copied summary retains the original bytes. Summary SHA256:
`2d992ffa67b8724af12e0ea4e0976779516670e69e3579eb6c486353c0468b9a`;
exported patch SHA256:
`ddb01f8afcc6c9184465e144d3997cc4361deca5008e605a85a786a0d8d9a239`.
The standalone patch and API report remain in the local capture collection;
the summary contains its patch and full final revalidation result.

The 16 copied files are autonomous live summaries whose names match their
12-hex run IDs: 15 CLI captures and one API/UI-created run summary. The latter
was also checked for equality with its API report's `run` object. API-report
duplicates, manual/probe files and other captures were excluded. The records
were checked for credentials, private keys,
token patterns, private local paths and nonfixture email addresses; none were
found. Their referenced URL hosts are public GitHub, Pydantic and Pytest
documentation. Missing historical provenance was not invented or rewritten.
Every copied file was verified byte-for-byte against its captured original.

Across all 16 terminal attempts, response-reported observations total **99
model requests, 312,946 input tokens and 155,918 output tokens**. Median ledger
duration is **58.661 s** and nearest-rank p95 is **106.409 s**, including failed
attempts across changing configurations. These are development measurements,
not a latency guarantee. Total cost and Sandbox operation counts remain unknown.

All recorded branch outcomes are retained: **19 failed and 17 passed branch
results**. Four early failed runs stopped before recording candidate results,
so an unrecorded branch is not counted as a pass or a failure. These branch
totals are not additional independent run attempts.

Broader reliability, three repetitions of the full suite, a measured
single-strategy comparison and public hosting remain pending. The fixture
source collection is published and verified as described below; all four new
run summaries are retained in [evaluation/evidence](../evaluation/evidence).

## Five cases and their current status

The implementation plan asks for five categories, preserved behavior and test
counts, repeated real integrations, latency, usage and failures. The existing
controlled fixture supplies one case. Four additional local packages make the
other cases concrete. They are distinct projects, not five labels applied to
the same exported run. [Machine-readable case definitions](../evaluation/cases.json).

| Case | Repository project path | Contract / expected minimum tests | Availability |
| --- | --- | --- | --- |
| validators | `fixtures/pydantic-v1-app` | Field/root validators, trimming, email normalization, aliases and nested models; 13 tests | 3 qualified successes / 12 development attempts at `afb82d4` |
| config | `evaluation/fixtures/config` | Alias and field-name population, whitespace stripping, forbidden extras, ORM attributes; 5 tests | 1 qualified success at public baseline `b8a1204` |
| serialization | `evaluation/fixtures/serialization` | Dictionary aliases, omitted `None`, nested output and JSON datetime contract; 4 tests | 1 qualified success at public baseline `b8a1204` |
| parsing | `evaluation/fixtures/parsing` | Object/JSON parsing, nested payloads, coercion and rejection; 4 tests | 1 qualified success at public baseline `b8a1204` |
| compatibility | `evaluation/fixtures/compatibility` | `pydantic` and `pydantic.v1` imports, dictionary boundary, coercion and validation; 4 tests | 1 qualified success at public baseline `b8a1204` |

All new packages start with `pydantic>=1.10.17,<2` and `.[test]`. They are small
behavioral fixtures, not representative samples of real production projects.
The compatibility case permits an intentional v1 compatibility module while
requiring the **installed distribution** to be Pydantic 2 after migration; do
not describe that result as removing every v1 API.

The four new local baselines were verified on 10 September in a fresh
Pydantic 1 environment, using each fixture as the working directory and its
`src` directory as `PYTHONPATH`: **config 5/5,
serialization 4/4, parsing 4/4 and compatibility 4/4 passed**. Their syntax and
authored test counts also match the manifest. The original controlled fixture's
13-test baseline has been observed passing in real Sandbox attempts.

These local results establish the **baselines**. Separate live evidence above
now establishes the four migration successes, with each real evaluation's
passing Pydantic 1 baseline commit, test count and test-contract digest retained.
Use the verified fresh environment for local checks;
the older `fixtures/pydantic-v1-app/.venv` stalled during import and was not used
to establish these new baseline results.

## Published source and repeatable cases

The API/CLI now accepts a validated `project_path`; the controlled repository's
default remains `fixtures/pydantic-v1-app`. This avoids creating four separate
repositories. All four additional packages were published in
[commit b8a1204ceaec260261c8fe1d695eae23c4597ae8](https://github.com/jsdhwfmax/branchshift-ai/commit/b8a1204ceaec260261c8fe1d695eae23c4597ae8).
On 10 September, anonymous HTTPS requests verified all **16 files**: each
manifest, package initializer, source module and behavior test matched the
local bytes exactly. The [verification record](evidence/fixture-publication.json)
retains the commit, timestamp, raw URLs, sizes and SHA256 hashes.

The four `public_repo_url` fields now point to the existing public repository.
This establishes public-source availability and content identity, not live
migration success, deployment or CI completion.

Keep tests and pytest configuration unchanged during migration. A passing
baseline is not a migration success; the winner and its clean-baseline
revalidation must run under Pydantic 2 and preserve the test fingerprint. Do
not edit tests to make a candidate pass or count skipped/missing tests as a
successful migration. The real pipeline validates its own test/patch evidence;
the aggregator only checks what the retained records assert.

## Collect actual attempts

Live execution is separate from the anonymous source check. An example
**real, credit-consuming** execution command is:

```sh
PYTHONPATH=services/api .venv/bin/python -m app.cli.live_run \
  --repo-url https://github.com/jsdhwfmax/branchshift-ai \
  --project-path evaluation/fixtures/config \
  --output /absolute/private-evidence/config-session
```

Keep every returned run JSON, including failed, cancelled and incomplete
attempts. Do not overwrite earlier failures after repairing the implementation.
Use a separate output/database directory for a standalone CLI session. **An
API process and an independently started CLI must not share an active run
database.** Startup recovery can otherwise treat another process's in-flight
work as interrupted; one worker/process owns a SQLite run database.

Record the model, baseline commit/path, orchestrator revision/content digest,
dirty state and runtime-config digest. Content digests permit reproducible
comparison while honestly disclosing uncommitted code; a clean Git checkout
is not a scoring condition. If settings, code or the baseline change, start a
new comparable series and retain the previous series as observed failures or
earlier results. Publish the corresponding final source with the submission.

## Aggregate retained records without executing anything

[app.cli.evaluate](../services/api/app/cli/evaluate.py) uses only the standard
library. It reads exported `RunSummary` JSON and API report envelopes containing
`run`; it does not initialize application settings, import providers, open a
database or call a service.

The supplied manifest maps one entry to each actual copied run. Paths resolve
relative to the manifest. For additional retained attempts, use the same
format; this example shows an existing evidence file:

```json
{
  "schema_version": 1,
  "attempts": [
    {
      "case_id": "validators",
      "path": "evidence/6d863a18d814.json"
    }
  ]
}
```

For older records, provenance may be added to the manifest only when supported
by contemporaneous evidence; accepted fields are `orchestrator_revision`,
`orchestrator_digest`, `orchestrator_dirty` and `runtime_config_digest`. Do not
invent digests for past runs or treat today's source hash as their runtime.
Embedded run provenance takes priority. Missing evidence stays missing.

```sh
PYTHONPATH=services/api .venv/bin/python -m app.cli.evaluate \
  --cases evaluation/cases.json \
  --attempts evaluation/attempts.json \
  --output /absolute/private-evidence/evaluation.md
```

This writes a Markdown matrix and adjacent `evaluation.json`. Default exit zero
means aggregation completed; it does not mean migrations passed. Add
`--require-complete` to require five cases with qualified success plus a
three-run trailing comparable success streak. Running the plan's complete
five-case evaluation three times requires at least **15 actual terminal case
attempts**, with failures included. The separate `three_successes_per_case`
field is stronger: every case has at least three qualified successes. The
current 16 development attempts do not meet it: four cases were run once and
the validators series includes development failures. Neither full-suite claim
follows from three repetitions of one fixture. Failures remain in the reported
denominators.

## What counts and what remains unknown

A qualified success requires a terminal live completion, the case's public
repository/path, pinned baseline commit and test fingerprint, sufficient
baseline tests, all three strategy results, a recorded NVIDIA model, retained
patch and a verified winner. Winner evidence must include all tests passing,
zero test/pip exits, Pydantic 2 and an unchanged test contract. The full
revalidation record must match the chosen strategy, patch and distinct
revalidation checkpoint and satisfy those same runtime/test conditions.

The three-success streak uses the latest chronological attempts for one case,
the same baseline commit/path, model, orchestrator content digest and runtime
configuration digest. A failure, mock/incomplete attempt, missing provenance or
changed runtime breaks it. Re-exporting a run does not add a trial: duplicate
run IDs are rejected. Different cases cannot be created by renaming the same
source path. The manifest is an explicit audit input; the tool cannot detect
attempts deliberately omitted from it.

The JSON includes test preservation, Pydantic version, revalidation gates,
recorded child-ID distinctness, failure category, source-file SHA256 and
observed model tokens/requests. It omits raw diagnostics, prompts, patches and
credentials from the aggregate. Retain original redacted exports privately
for review; do not assume identifier-only summaries authenticate the provider.

Median/p95 use all terminal live attempts' `updated_at - created_at`, including
queue time and final writes. p95 uses the nearest-rank convention; with three
trials it is simply the maximum. These are descriptive ledger timings, not
isolated inference or Sandbox execution latency.

Model token totals are response-reported observations. Failed requests may
have incomplete billing evidence. **Total dollars/credits and Sandbox operation
counts remain unknown** until actual rates, complete usage and operation
instrumentation exist. Do not infer operations from three child IDs, assume
zero cost for missing usage, or multiply tokens by an uncited price.

## Validation of this local harness

The 18 aggregation tests pass and Ruff passes for the new CLI/tests. The
integrated validation reported **202 API tests and 27 web tests passing**,
with API lint/type checks and frontend lint/build passing. These implementation
checks include protected patch paths, altered test contracts, missing/skipped
test evidence and rejected revalidation; they are distinct from the actual
provider records. Tests use explicitly synthetic records in pytest temporary
directories; none are placed in the actual attempt manifest. They cover mock
exclusion, missing/mismatched revalidation, altered tests, duplicate exports,
same-fixture repetition, dirty but identical runtime content, changed settings,
failure denominators and unknown usage/cost.

The actual 16-record manifest was aggregated with `--require-complete` and
passed: seven qualified successes cover all five cases, and the validators
case retains its three consecutive comparable successes. All nine failed
attempts remain included. The generated JSON hashes match the unchanged input
bytes. Full-suite repetition and standalone-strategy versus three-strategy
comparison remain separate work until their actual evidence exists. Passing
local adverse-input checks and these controlled cloud runs do not establish
exhaustive adversarial Sandbox security.
