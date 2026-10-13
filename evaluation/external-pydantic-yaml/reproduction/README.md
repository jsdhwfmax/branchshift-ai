# Retained sources for audit and reproduction

The three `runtime-*` directories contain the authored BranchShift app Python files, package manifest and MIT license from exact Git commits. The digest of all 42 app Python files was independently reconstructed and matches the corresponding session's `implementation_digest`:

| Runtime snapshot | Session |
| --- | --- |
| `runtime-0cbd95cb` | Initial two planner calls in `model-session` |
| `runtime-4591b7a` | Remaining eight calls in `schema-fixed-session` |
| `runtime-b78e394` | Five-call `line-edit-session` |

[Source provenance](source-provenance.json) contains full commits, public links, file counts and verified digests. The files were read from those committed sources; none was executed while assembling this bundle.

`helpers/first-iteration.py`, `helpers/schema-fixed.py` and `helpers/line-edit.py` retain the study helpers. Their normal mode advances/replays retained evidence without calling a model; live calls require the explicit call flag and an environment credential. Session manifests freeze source, model inputs and request budgets. Do not reset or reinterpret existing reservations as unused. The line-edit helper hash matches its retained follow-up receipt.

`external-runner/run_comparator.py` is the exact comparator runner whose SHA-256 appears in run 38331091063. `external-runner/run_candidate.py` was prepared for subsequent candidate validation but **was not invoked** in either AI iteration. These files depend on the matching BranchShift app source and their original study directory layout; preserve their package/import context in an isolated execution runner. They are not evidence that the user's host ran upstream code.

The comparator's original [command ledger](../run-38331091063/evidence/commands.json), [baseline environment](../run-38331091063/evidence/baseline/pip-freeze.txt), [tool environment](../run-38331091063/evidence/tool/pip-freeze.txt), [candidate constraints](../run-38331091063/evidence/candidate-environment/constraints.txt), and [runner identity](../run-38331091063/evidence/runner.json) describe what actually ran. Version freezes do not guarantee future package availability or deterministic model responses. Original model payloads and responses are the observed records; a new execution would be a new result.

The private credential-loading invocation wrappers, account records, `.env` files, full Git checkouts, binary archives and local environments are intentionally absent. No bundled script contains a credential value. Both the upstream and codemod MIT licenses remain with the runner evidence; BranchShift's license accompanies each runtime snapshot.
