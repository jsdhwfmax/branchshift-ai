# Private hosted acceptance — 13 October 2026

The [private preview](https://branchshift.onrender.com) completed one real
Safari-started migration. The [retained run](https://branchshift.onrender.com/runs/e9290cae7c9c)
requires the separately supplied access credentials. No credentials or full
provider report are published here. This summary and the [machine receipt](receipt.json)
retain aggregate observations and hashes of the private exports.

The observations occurred on 13 October in Sydney, 12 October UTC. They cover
one controlled fixture and one deployment; they do not extend the earlier
[15-run cohort](../../../evaluation/series-20260910/README.md) to this runtime
or establish general migration reliability.

## Deployment and source identity

Render's control plane reported deployment commit
[`2480ed91dac5cc70e3a9486acaa2ea41c04ab8f2`](https://github.com/jsdhwfmax/branchshift-ai/tree/2480ed91dac5cc70e3a9486acaa2ea41c04ab8f2)
live at **2026-10-12 23:43:49 UTC**. The matching
[CI run](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/38323270878)
completed successfully. The migration baseline independently records that
same repository commit.

The run's `orchestrator_revision` and dirty-checkout status are **null**.
An independent download of that exact public commit reproduced its recorded
source-content digest across **42 files**, using the existing
[provenance algorithm](https://github.com/jsdhwfmax/branchshift-ai/blob/2480ed91dac5cc70e3a9486acaa2ea41c04ab8f2/services/api/app/provenance.py):
the API's Python source files and `pyproject.toml`. This verifies the content
covered by that algorithm, not the whole image, frontend assets, installed
dependencies or runtime configuration. The receipt retains both the verified
source digest and the recorded runtime-config hash. Missing runtime revision
and dirty-checkout values remain null.

## Live migration result

Run `e9290cae7c9c` completed in **79.717 seconds**, measured from ledger creation
to final save. The baseline passed 13 original tests. The exact model was
`nvidia/Nemotron-3-Ultra-550b-a55b` on Nebius Token Factory.

| Candidate | Result | Tests passed / collected | Lint findings | Changed lines |
| --- | --- | ---: | ---: | ---: |
| minimal | Failed during test collection | 0 / 2 | 1 | 37 |
| compatibility | Passed | 13 / 13 | 1 | 82 |
| refactor | Passed; selected | 13 / 13 | 1 | 55 |

Refactor and compatibility tied on test ratio, dependency consistency and
lint. Refactor won on fewer changed lines. The selected patch then passed
**13/13 tests from a distinct clean-baseline checkpoint**, with actual Pydantic
2, successful dependency and test exits, and the original test contract
preserved. The downloaded patch matches the winner and revalidation records.

Limitations remain visible: refactor and its revalidation each recorded
**25 pytest warnings and one unused `typing.Optional` import**. Compatibility
recorded 14 warnings. The stored diagnostics give warning counts without
enumerating their categories. Minimal retained two collection errors caused
by an unsupported `model_validator(skip_on_failure=True)` argument.

## Observed access and evidence retention

- The primary browser observer verified Safari's actual completed page,
  JSON and patch downloads, and the completed state after page refresh.
  An independent file comparison matched both downloads to HTTP exports.
- A GET-only collector replayed all **24 retained events**, intentionally
  disconnected after event 1, then received only events 2–24 with
  `Last-Event-ID: 1`. The combined stream exactly matched the report ledger.
  This checks completed-run replay and HTTP reconnection, not a live browser
  EventSource interruption.
- Repeated JSON and Markdown exports were byte-identical. Raw exports remain
  private; their byte counts and SHA-256 hashes are in the receipt.
- Before the live run, a Render Web Shell read on replacement instance
  `ffnlk` found the prior instance's database marker and `integrity_check=ok`.
  This demonstrates retention across that replacement, not a later restart
  of this completed run or a backup-recovery test.

All eight recorded model requests returned usage: **36,468 input / 17,487
output tokens**. The adapter recorded **16 completed SDK calls**: one image
use, nine runs and six reads. These are observed calls, not billed operations
or monetary totals.

The **daily limit of 1** was a commissioning setting. It does not establish
the final judge allowance or continuous availability; access capacity must be
set before submission. This record makes no entrant declaration or claim of
final submission readiness.
