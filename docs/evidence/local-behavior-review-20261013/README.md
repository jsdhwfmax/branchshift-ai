# Behavior gap found by local replay

The retained hosted winner for run `e9290cae7c9c` passed the authored example's
13 original tests, and the same patch passed its clean-baseline check. A local
replay on 2026-10-13 found a behavior difference outside those tests.

| Explicit input | Original model | Selected patch |
| --- | --- | --- |
| Whitespace-only name | Rejected | Rejected |
| Name `"  Ada  "` | Accepted, normalized to `"Ada"` | Same JSON result |
| Numeric name `123` | Accepted, normalized to `"123"` | Rejected |

Each case uses the same fixed ID, email and timestamp on both sides. This is a
review finding, not a claim that numeric names must remain accepted. A maintainer
must decide whether the changed contract is intended.

The replay used Python 3.13.9, Pydantic 1.10.26 for the original model and
Pydantic 2.13.5 for the patched model, with no `pydantic.v1` fallback. These are
local replay environments; they do not reproduce every dependency or runtime
detail of the historical Sandbox. The same source commit and exact retained
patch were checked, and `git apply --check` and application both succeeded in
a scratch copy. No historical evidence was overwritten and no provider call
was made.

[The observations](observations.json) retain the fixed inputs, normalized JSON,
exception class, versions, source hashes and patch identity. This evidence
motivated BranchShift's optional [behavior review](../../behavior-review.md):
passing original tests and matching explicit examples are separate statements.
It does not establish behavior equivalence or performance on external projects.
