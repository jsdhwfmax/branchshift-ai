# External case: no successful native-v2 migration demonstrated

This evidence records one fixed historical version of **pydantic-yaml**, the official **bump-pydantic** comparator, and two disclosed AI development iterations. Neither approach achieved the case's native-v2 acceptance conditions. This is a failed external-case study, not a general success-rate benchmark or evidence that BranchShift outperforms the codemod.

| Arm | Observed result | Runtime test outcome |
| --- | --- | --- |
| Original Pydantic 1 baseline | 14 passed, one original xfail | Baseline accepted |
| Official codemod | Command completed; 14 changed lines across four files | Eight test-module import/collection errors, reproduced from the clean copy |
| AI full-source replacements | 10 calls, including three planner requests; no applicable candidate | Not run |
| AI bounded line edits | Five further calls, same saved plan, no new planner call; no applicable candidate | Not run |

The original suite's `test_readme` has no assertions, and the original xfail remains visible. The codemod's eight collection errors are **not eight executed test failures**. AI BranchResult zero counts mean tests were never reached; they are **not “0/15 tests passed.”** No AI candidate reached dependency validation, the native-v2 probe or clean-patch revalidation.

The [detailed report](comparison-report-draft.md) links immutable source commits, original results, exact patches and licenses. The [first AI record](ai-full-replacement-iteration-20261013.json) preserves the exhausted ten-call iteration: minimal failed, while compatibility/refactor remained incomplete. The [line-edit record](ai-line-edit-iteration-20261013.json) preserves the closed follow-up: minimal/refactor failed source prechecks and compatibility aborted on an explicit output-length error without a terminal BranchResult. It used five of six allowed calls; the unused allowance was not spent.

All **15 responses have reported token usage**. The [combined model estimate](combined-model-cost-receipt.json) is **US$0.756100**, using observed standard synchronous input/output prices. It is not an invoice and excludes taxes, Render, Sandbox and other services. The earlier theoretical envelopes remain historical planning records, not actual charges.

The baseline/codemod checks ran on an **independent GitHub-hosted runner**, not in Nebius Sandboxes. AI proposals used real NVIDIA Nemotron calls through Nebius Token Factory; none reached that independent runtime validator. These adaptations must remain separate from the deployed BranchShift Sandbox pipeline and its earlier authored-fixture cohort.

The study informed tighter planner constraints, accurate patch-check wording, bounded line edits and explicit output-limit diagnostics. Later changes add bounded output-limit repair at [`6e310fc`](https://github.com/jsdhwfmax/branchshift-ai/commit/6e310fc72ec1e651fb947a732e4bd63658e86a83) and a narrow explicit-path planning guard at [`cf89bdf`](https://github.com/jsdhwfmax/branchshift-ai/commit/cf89bdfdefe50669f4ec0f8fbe00397be7787499). The latter now rejects the saved plan's undeclared shim path in an offline check. Both are **local-test evidence only**, outside the frozen study, with no new model rerun. Path checking cannot establish correct API reasoning; a permitted, valid patch that preserves the original behavior remains unproven.

- [Current protocol and history](plan.md)
- [Full comparator run](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38331091063) and [retained earlier harness failure](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38330924173)
- [Frozen scripts, runtime snapshots and provenance](reproduction/README.md)
- [Upstream MIT license](run-38331091063/evidence/upstream-LICENSE) and [codemod MIT license](run-38331091063/evidence/codemod-LICENSE)
- [Artifact inventory and verification](publication-manifest.json)

Original session files and runner evidence are preserved unchanged. Historical snapshots may describe a then-pending follow-up; this README and the detailed report state its final observed outcome. Reusable scripts and evidence are included, not credentials, local account files, environment directories or source archives.
