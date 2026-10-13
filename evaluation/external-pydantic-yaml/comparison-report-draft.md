# One external Pydantic migration case — retained comparator evidence

Updated 2026-10-13. The upstream baseline and official codemod have run. Two disclosed AI proposal iterations used 15 model calls without producing a candidate that could enter runtime validation. Both iterations are closed. Preparing this report only read retained artifacts; it made no inference requests, Sandbox operations or third-party source executions.

## Observed result

On this fixed historical version of `pydantic-yaml`, the original suite passed under Pydantic 1.10.24 with **14 passed and one original expected failure**. `bump-pydantic` finished normally and produced a candidate, but that candidate could not import under Pydantic 2.12.5. Pytest reported **eight test-module collection errors**, and the same errors recurred after applying the exact patch to a clean copy.

| Stage | Installed Pydantic | Original suite | Dependency check | Native-v2 structural check | Original tests/configuration |
| --- | --- | --- | --- | --- | --- |
| Upstream baseline | 1.10.24 | 14 passed; 1 original xfail | Passed | Not a v2 target | Preserved |
| Official codemod candidate | 2.12.5 | 8 module collection errors; no test bodies executed | Passed | Blocked by import error | Preserved |
| Exact codemod patch on clean copy | 2.12.5 | Same 8 module collection errors | Passed | Same import error | Preserved |
| First AI full-source-replacement iteration | No candidate runtime | Tests not run; no applicable candidate | Not run | Not run | No runtime patch applied |
| Additional line-edit iteration | No candidate runtime | Tests not run; no applicable candidate | Not run | Not run | No runtime patch applied |

The candidate changes **14 lines across four files**, counting additions plus deletions. This includes the shared dependency requirement change from Pydantic 1 to `>=2,<3`; no hand-written code repair was added to the codemod result. The patch retains codemod TODOs for work the tool could not complete. The lint count is 51 at baseline and 52 after the codemod, but neither lint nor patch size rescues a candidate that cannot run its original suite.

The raw aggregate's `tests_collected=8` and `tests_failed=8` summarize eight JUnit error records. They must **not** be described as eight executed tests failing, or as an eight-test replacement for the original 15 collected cases. Both candidate JUnit files explicitly contain `errors=8`, `failures=0`; pytest exits with code 2 during collection. The retained error is an import of `Protocol` from `pydantic.parse`. The native-v2 probe also cannot import the library: its recorded `false` does not establish which model API a successfully loaded library would use.

Baseline coverage has two important limits. `test_secret_types_roundtrippable` is already marked xfail because YAML/JSON encoder support is absent; the harness preserves that status. `test_basic.py::test_readme` has only a docstring and no assertions. It remains one of the 14 passed cases, but is not substantive behavior coverage.

## Source, environment and attribution

The study unit is the complete upstream package and its original test tree, not an extracted authored fixture:

- Upstream: [`NowanIlfideme/pydantic-yaml` at `54ff4bad7bca758a9dd22a791b707a2b9c27159e`](https://github.com/NowanIlfideme/pydantic-yaml/tree/54ff4bad7bca758a9dd22a791b707a2b9c27159e), corresponding to v0.11.2. The retained manifest contains 41 tracked files totaling 64,297 bytes.
- Comparator: [official `pydantic/bump-pydantic` at `a111d4177405dbf61ef59035adaa0639b17b8718`](https://github.com/pydantic/bump-pydantic/tree/a111d4177405dbf61ef59035adaa0639b17b8718). The command was `bump-pydantic src/pydantic_yaml`, using a separate tool environment. Its exit code is zero and its error log is empty.
- [Upstream MIT license](run-38331091063/evidence/upstream-LICENSE): copyright 2020 Anatoly Makarevich; SHA-256 `97128793d72c6be0a21bdfd2405312d827dd87e0bbd8fc5c904ec2c37e7057e0`.
- [Comparator MIT license](run-38331091063/evidence/codemod-LICENSE): copyright 2023-present Marcelo Trylesinski; SHA-256 `5b6b88b8ca70688935c81d96b9b6d343edb059bccad07c763039205d09de4f3a`. Preserve both license texts and attribution with any redistribution.

The actual execution used a **GitHub-hosted Ubuntu runner and Python 3.12.15**, filesystem copies and independently built virtual environments. It did not use Nebius checkpoints, and its artifacts correctly retain null checkpoint/image UUIDs. This is an explicit execution-environment adaptation from the earlier proposed Sandbox protocol, not evidence of the hosted BranchShift application or Sandbox performance. The historical upstream CI used older Python versions; this report does not claim its Python 3.12 setup was an upstream-tested matrix.

The suite command was `python -m pytest -q src/pydantic_yaml/test -ra --tb=short --junitxml=...`. Both candidate checks used Pydantic 2.12.5, pytest 8.3.5, PyYAML 6.0.2 and semver 3.0.4. Ruff was 0.13.0. Build/tool dependencies were explicitly pinned; editable project installation used the original `pyyaml,semver` extras with no build isolation. Full commands and installation reports are retained, rather than implying that this matches an untouched upstream development environment.

Version records are the [baseline freeze](run-38331091063/evidence/baseline/pip-freeze.txt), [codemod freeze](run-38331091063/evidence/codemod/pip-freeze.txt), [clean resolved requirements](run-38331091063/evidence/clean/resolved-requirements.txt), and [separate tool freeze](run-38331091063/evidence/tool/pip-freeze.txt). The [candidate environment constraints](run-38331091063/evidence/candidate-environment/constraints.txt) have SHA-256 `09cb776346095a5716b5ef8fb1b655bd9f7dafa615adaf7a6f0bdb2028abb007`. These are version pins and observed freezes, not hash-pinned package archives or a portable image digest. Candidate and clean resolved-version maps match exactly.

## Execution history and reproducibility

- [First execution: run 38330924173](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38330924173), runner source `ed913cae13851a924ab26c2c3824408477cf7369`: the baseline passed, then the harness stopped while trying to read a missing tool license path. Its [failure summary](run-38330924173/evidence/summary.json) remains retained. This was a harness setup failure, not a failed codemod migration or a second independent case.
- [Completed comparator execution: run 38331091063](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38331091063), runner source `451a5f60f017e70132b95f6a7d7cc8396e3f009e`: baseline, codemod and clean-copy checks all produced artifacts. The runner script SHA-256 is `607953f48e8beb23e0795ecf252e1a2d4fd39fe8b775431a630f06a04c50eb54`. A completed workflow/comparison does not mean the migration passed.

The [actual protocol](run-38331091063/evidence/protocol.json), [command ledger](run-38331091063/evidence/commands.json), [summary](run-38331091063/evidence/summary.json), and [baseline](run-38331091063/evidence/baseline/junit.xml), [candidate](run-38331091063/evidence/codemod/junit.xml) and [clean](run-38331091063/evidence/clean/junit.xml) JUnit files support the table above.

The original test tree was restored after the codemod processed the package, since tests are nested inside it. Nine before/after/final contract records across the three stages match exactly, covering 11 test-tree files and pytest configuration. Their digest is `b904563f71d38851af139911231703c997a1f56d6840690d9802c386c928a61c`. All 41 baseline source-file records also match before and after the experiment.

The [candidate patch](run-38331091063/evidence/codemod/candidate.patch) has SHA-256 `782dddfc417c48ed998e759092546f2862c6c150eae2100cb7e9569e95f5edaa`; the clean-copy resulting diff matches byte-for-byte. Patch application and dependency checks passed; original-outcome preservation and native-v2 acceptance did not. A [local verification receipt](comparison-report-verification.json) records the checks and source-artifact hashes without rewriting the original results.

## First AI iteration — ten requests, no runtime candidate

Real NVIDIA `Nemotron-3-Ultra-550b-a55b` requests with thinking enabled generated plans and proposed complete replacement source files. They used the same retained upstream baseline, citations and candidate dependency constraints. This was a proposal-generation session for independent GitHub-runner validation, not an end-to-end Nebius Sandbox run. No candidate passed source/schema prechecks, so none reached the runtime validator, original suite, native-v2 probe or clean-patch check.

| Phase | Observed model requests | Retained outcome |
| --- | ---: | --- |
| Original planner | 2 | First response rejected: minimal had 11 steps, beyond the 1–8 gate. Second response had invalid structured content at 16,384 output tokens. |
| Planner after schema fix | 1 | Plan accepted; each of the three strategies has eight ordered steps. |
| Minimal editor | 3 | First response failed source syntax precheck; the next two failed structured-content validation. A terminal failed result is retained. |
| Compatibility editor | 2 | Source syntax precheck failure, then invalid structured content. Third request prepared but not sent; branch remains incomplete. |
| Refactor editor | 2 | Both responses failed source syntax precheck. Third request prepared but not sent; branch remains incomplete. |
| Total | **10** | Original request allowance exhausted; no runtime candidate. |

The first two planner requests are retained in [model-session](model-session/manifest.json). After the schema correction at [`4591b7aace1741483baf9a005c3d4797f24a93a3`](https://github.com/jsdhwfmax/branchshift-ai/commit/4591b7aace1741483baf9a005c3d4797f24a93a3), [schema-fixed-session](schema-fixed-session/manifest.json) used the remaining eight requests. The sessions have distinct implementation digests; this is a disclosed harness revision inside one ten-request development allowance, not a frozen-method repeatability cohort.

The [saved plan](schema-fixed-session/plan/result.json) has SHA-256 `5b2f7116f410b7add9ae38ebdc70d1840f79a774904091cb920159fdae4fdbf0`. Planning success means that the output passed its schema and planning gate; it does not establish that its proposed API changes are correct. Source prechecks caught malformed quoting, including unterminated strings and literal `u0022` sequences where Python syntax was required. Responses that reached the output limit and failed structured validation are reported as such; the retained evidence does not independently prove a provider truncation reason.

[Minimal's result](schema-fixed-session/minimal/result.json) says failed because no safe applicable patch was produced after three attempts. Its stored zero test counts mean **tests were not executed**, not “0/15 tests passed.” Compatibility and refactor have no terminal result files. Their prepared third-request files have neither reserved-call records nor responses, so they do not count as additional calls or completed failed branches. Original request/response records and diagnostics remain unchanged.

The [machine-readable iteration record](ai-full-replacement-iteration-20261013.json) identifies all ten reservations and responses, distinguishes parsing from source-precheck failures, and retains hashes for 42 source artifacts. It confirms complete returned-usage coverage: **152,486 input tokens and 116,347 output tokens**. At the [observed standard synchronous prices](model-pricing-receipt.json) of $1/$3 per million input/output tokens, the [first-iteration usage estimate](full-replacement-cost-receipt.json) is **US$0.501527**. This is an inference estimate, not an invoice; tax is unknown and hosting, Sandbox and other service charges are excluded.

## Additional editing-method iteration — closed after five calls

The [declared follow-up](line-edit-followup-protocol.json) replaced full-source replacement with bounded line edits and reused the exact saved plan above. It made **zero new planner calls** and used **five of its maximum six additional model calls**, outside the original ten-request allowance. This is an additional development iteration after a method change, not extra attempts hidden inside the first budget or evidence of improvement under an unchanged method.

The frozen implementation is [`b78e394ba2be765cf5002ea7d995b6d78fe8c1ce`](https://github.com/jsdhwfmax/branchshift-ai/commit/b78e394ba2be765cf5002ea7d995b6d78fe8c1ce), app digest `1872a466be38554defb6fbe98d44fdc6bbd0e2f0b67a3ccad8239cc7d9260b02`. The [follow-up receipt](line-edit-session/followup-receipt.json) records helper SHA-256 `4d94ec23a4fa14b9dfb0339385901ee14a57b542bb7469a249ca8f3bf6de1b2e`, unchanged plan bytes and the explicit two-attempt limit per strategy, adapted from the production default of three. No plan, source or checkpoint reuse is implied beyond those recorded inputs.

| Strategy | Actual calls | Last observed outcome | Retained terminal BranchResult |
| --- | ---: | --- | --- |
| Minimal | 2 | First proposal had overlapping edit ranges; second exceeded the total edit-size limit | Failed |
| Compatibility | 1 | Explicit provider `finish_reason=length`; the frozen code aborted this phase | None; provider exception retained |
| Refactor | 2 | First proposal exceeded the total edit-size limit; second left an unclosed `(` at `mixin.py:113` | Failed |

All five calls have responses and complete usage. Both repairable strategies exhausted their two attempts; compatibility's provider exception was not repairable in this frozen version. The sixth call allowance was left unused. Minimal/refactor result objects contain zero test counts as defaults because execution never began; there is **no 0/15 test result**. Compatibility has no terminal BranchResult, and the report does not invent one.

The [line-edit machine record](ai-line-edit-iteration-20261013.json) retains all reservations, responses and diagnostic provenance. The [line-edit cost receipt](line-edit-cost-receipt.json) reports **103,727 input tokens and 50,282 output tokens**, for an inference estimate of **US$0.254573**. The [combined receipt](combined-model-cost-receipt.json) records **15 calls, US$0.756100 estimated model inference, one independent case and zero runtime candidates**. Neither estimate is an invoice; taxes, Render, Sandbox and other services are excluded.

Before execution, the conditional six-call envelope was US$1.194912 additional and US$1.696439 combined. It assumed at most 150,000 billed input tokens per 150,000-byte input bound plus 16,384 output tokens per request, at $1/$3 per million. Those figures remain a declared conditional ceiling calculation, not observed spend or a cash hard cap. Actual returned usage above is the observed estimate.

The same fixed upstream commit, original tests, target dependency environment and library-specific native-v2 probe remain required for comparison. Installing Pydantic 2 while using its v1 compatibility API is not a native-v2 result. No AI patch reached that gate. Independent GitHub-runner candidate execution was prepared but not invoked, and must not be described as a deployed Nebius Sandbox run.

## Product changes and the remaining blocker

The evidence led to tighter planner step-count constraints, explicit patch-check rather than native-migration success wording, a bounded line-edit option, and visible provider output-length diagnostics. The later [`6e310fc72ec1e651fb947a732e4bd63658e86a83`](https://github.com/jsdhwfmax/branchshift-ai/commit/6e310fc72ec1e651fb947a732e4bd63658e86a83) adds bounded repair for explicit output-length failures. That later change is covered by local unit tests only; it was **not** part of either frozen model iteration and has not been re-run against this external case.

The remaining issue is producing a coherent, permitted patch with correct Pydantic API reasoning. The saved compatibility plan asks for a new `pydantic_shim.py` file outside the editor's allowed existing source paths. The later [`cf89bdfdefe50669f4ec0f8fbe00397be7787499`](https://github.com/jsdhwfmax/branchshift-ai/commit/cf89bdfdefe50669f4ec0f8fbe00397be7787499) adds a narrow planning guard: offline validation now rejects that unchanged plan. Its 42 planner tests, Ruff and mypy passed, but no model was re-run. This guard checks explicit slash-qualified `.py` paths, excludes URLs and ignores dotted API names; it cannot prove API semantics or identify paths a plan never spells out. An accepted plan is not a correctness proof, and a candidate still needs original-outcome preservation, native-v2 qualification and exact clean-patch revalidation. No further model calls are reported or implied here.

## What this case can and cannot establish

The observed finding is narrow: this official codemod invocation did not complete a working migration for this historical library under the recorded environment, and two AI development iterations totaling 15 calls did not produce a runtime-testable patch. Neither method has demonstrated a successful native-v2 migration on this case. No AI superiority is established. One upstream project cannot establish a general success rate, and the earlier five authored fixtures remain a separate cohort. Three strategies still represent one project-level comparison—not three independent projects, a matched-budget ablation or a cost-saving study. No total invoice or general speed advantage is established by these artifacts.
