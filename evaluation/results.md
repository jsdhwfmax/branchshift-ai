# Retained migration evaluation

Generated locally from the explicitly supplied export manifest. No providers were called.
The manifest must include failed attempts; this tool cannot discover omitted runs.

Qualified successes: 3 / 12 terminal live attempts.
Independent cases with success: 1; five-case gate: False; three-consecutive gate: True.

At least three qualified successes on every case: False.

| Case | Attempts | Live terminal | Qualified success | Trailing same-runtime streak |
| --- | ---: | ---: | ---: | ---: |
| validators | 12 | 12 | 3 | 3 |
| config | 0 | 0 | 0 | 0 |
| serialization | 0 | 0 | 0 | 0 |
| parsing | 0 | 0 | 0 | 0 |
| compatibility | 0 | 0 | 0 | 0 |

| Run | Case | Status | Winner | Qualified | Unmet gates | Input/output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| f45d8d865b50 | validators | failed |  | False | live_completed, baseline_contract, three_results, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 4923 / 1943 |
| e0f5f9a34a45 | validators | failed |  | False | live_completed, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 24694 / 9289 |
| 38e8284b4fe3 | validators | failed |  | False | live_completed, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 25632 / 6511 |
| 866e14413018 | validators | failed |  | False | live_completed, three_results, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 0 / 0 |
| c4db91327858 | validators | failed |  | False | live_completed, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 25860 / 7561 |
| 88c20bab4e91 | validators | failed |  | False | live_completed, three_results, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 7350 / 1589 |
| 23c4e360b67a | validators | failed |  | False | live_completed, three_results, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 0 / 0 |
| 65d80241c3dc | validators | failed |  | False | live_completed, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 21690 / 58335 |
| 1d3583ee632a | validators | failed |  | False | live_completed, winner_passed, test_contract_preserved, pydantic_2, tests_pass, dependencies_pass, patch_retained, revalidation_recorded, revalidation_pass | 43769 / 8132 |
| 6d863a18d814 | validators | completed | compatibility | True | none | 35389 / 15952 |
| 83489c0de0de | validators | completed | compatibility | True | none | 34076 / 12274 |
| aedb7bf272f4 | validators | completed | minimal | True | none | 24663 / 18472 |

Median ledger duration: 64.4785 seconds. p95: 106.409 seconds (nearest rank).
Durations include queue time and final writes; small-sample p95 is descriptive.

Observed model usage (response-reported totals, not complete billing):
- observed_model_requests: 79; field present in 12 terminal live records.
- observed_input_tokens: 248046; field present in 12 terminal live records.
- observed_output_tokens: 140058; field present in 12 terminal live records.

Total cost and Sandbox operation counts: **unknown**, not zero.
Revalidation is a retained-ledger assertion; this tool does not replay the patch or independently authenticate provider evidence.
Streaks require the same case/path, baseline commit, NVIDIA model, orchestrator content digest and runtime-config digest. Dirty state is disclosed, not excluded.
