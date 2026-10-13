# Manual native-v2 control

This control was **authored directly with Codex, with zero evaluated Nebius/Nemotron API calls**.
Codex assistance is AI assistance; `model_calls_scope: evaluated_nebius_provider_only` identifies
what the machine-readable `model_calls: 0` field counts. This is not
an autonomous BranchShift success or a Nebius Sandbox run. It uses the original fixed
Pydantic YAML checkout, full v2 dependency constraints, original tests (14 passed and one
existing xfail at baseline), test/configuration contract, and independent native-v2 check.
The two scripts in `protocol/` are unchanged byte copies from main commit `58ff031`.

One invocation validates one candidate. The human-controlled ledger permits at most four
manual iterations, then one clean repeat of a qualified patch. `manual_iteration` must be
1–4; the workflow does not retry automatically. The iteration field is not a durable global
dispatch counter: the executing maintainer is responsible for that total budget.

Inputs are `candidate-input/{request.json,candidate.patch,command.sh}`. The request must
declare `authoring_method: manual_codex_assisted`, `model_calls: 0`, and its iteration.
The retained edit proposal, strategy, and protocol receipt document authorship and generation.
`--check-only` verifies metadata, byte anchors, and the original fixed-case input contract
without installing packages, executing a candidate, or making network requests.

The workflow is restricted to branch `evaluation/manual-native-20261013`, Ubuntu 24.04,
Python 3.12.15, and the first workflow attempt. No user secrets, persisted checkout
credentials, package cache, or image cache are configured. Candidate subprocesses receive
the original runner's allowlisted environment. A standard GitHub runner may still access
the network; this is not a claim of a network isolation boundary.

The artifact is at most 5 MiB and retained for one day. It always contains `summary.json`
and `validation/application-check.json`; if setup stopped early, the application result is
explicitly `not_completed`. Full artifacts preserve commands, patch, JUnit/outcomes, logs,
runtime locks, the independent comparison/native check, and original application checks.
Summary JSON and archive SHA are also written to the public job summary.

`candidate_native_migration_qualified` requires the unchanged independent test/native/pip
gate, exact candidate tree and full runtime, preserved test contract, and successful original
test/install/pip markers with all 15 original test identities preserved. The original xfail
may stay skipped or become passed, matching the existing protocol. Lint is recorded but is
not a new migration gate. A green job means evidence collection completed, not that a failed
candidate qualified; inspect the qualification field and application check.

For the single clean repeat, keep `candidate.patch` and `command.sh` byte-identical, change
the request phase to `revalidation`, and retain the same `manual_iteration`. Add the prior
qualified manual artifact's `summary.json` and `validation/application-check.json` under
`qualified-control/`. Their contents and hashes are checked before a fresh checkout/runtime
is created. Previous failed artifacts remain in the experiment ledger; the harness does
not re-execute earlier candidates or the original baseline/codemod comparison.
