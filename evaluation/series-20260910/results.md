# Retained migration evaluation

Generated locally from the explicitly supplied export manifest. No providers were called.
The manifest must include failed attempts; this tool cannot discover omitted runs.

Qualified successes: 15 / 15 terminal live attempts.
Independent cases with success: 5; five-case gate: True; three-consecutive gate: True.

At least three qualified successes on every case: True.

| Case | Attempts | Live terminal | Qualified success | Trailing same-runtime streak |
| --- | ---: | ---: | ---: | ---: |
| validators | 3 | 3 | 3 | 3 |
| config | 3 | 3 | 3 | 3 |
| serialization | 3 | 3 | 3 | 3 |
| parsing | 3 | 3 | 3 | 3 |
| compatibility | 3 | 3 | 3 | 3 |

| Run | Case | Status | Winner | Qualified | Unmet gates | Input/output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| 3c96a45e7a8b | validators | completed | minimal | True | none | 28373 / 18817 |
| 2e86cf16dfc0 | config | completed | refactor | True | none | 19939 / 5627 |
| eea3304afbe6 | serialization | completed | compatibility | True | none | 12854 / 4249 |
| b6475ac669f8 | parsing | completed | minimal | True | none | 12545 / 2774 |
| 97b310dcbde7 | compatibility | completed | minimal | True | none | 12746 / 3703 |
| 73347c34a2ef | validators | completed | minimal | True | none | 28406 / 24141 |
| f87a0a787413 | config | completed | refactor | True | none | 19939 / 5673 |
| 6bc43693144a | serialization | completed | compatibility | True | none | 19834 / 5039 |
| 67cfd318e689 | parsing | completed | minimal | True | none | 12545 / 2731 |
| e6dd367c1436 | compatibility | completed | minimal | True | none | 12746 / 5038 |
| b93c8df744ac | validators | completed | compatibility | True | none | 37961 / 30178 |
| ee4ce9911531 | config | completed | minimal | True | none | 19804 / 5023 |
| f3f3b10e5df1 | serialization | completed | compatibility | True | none | 12854 / 4178 |
| 2d501a3e059f | parsing | completed | minimal | True | none | 12342 / 4350 |
| b249a85a9f78 | compatibility | completed | minimal | True | none | 12746 / 4710 |

Median ledger duration: 53.022 seconds. p95: 114.892 seconds (nearest rank).
Durations include queue time and final writes; small-sample p95 is descriptive.

Observed model usage (response-reported totals, not complete billing):
- observed_model_requests: 79; field present in 15 terminal live records.
- observed_input_tokens: 275634; field present in 15 terminal live records.
- observed_output_tokens: 126231; field present in 15 terminal live records.

Observed Sandbox adapter SDK calls: {'attempted': 176, 'completed': 176, 'failed': 0, 'cancelled': 0}; complete counters in 15 terminal live records.
These count adapter calls, excluding SDK polling/retries and billable units.
Total cost and billable Sandbox operation counts: **unknown**, not zero.
Revalidation is a retained-ledger assertion; this tool does not replay the patch or independently authenticate provider evidence.
Streaks require the same case/path, baseline commit, NVIDIA model, orchestrator content digest and runtime-config digest. Dirty state is disclosed, not excluded.

## Declared series

```json
{
  "planned_rounds": 3,
  "planned_attempts": 15,
  "recorded_attempts": 15,
  "all_planned_slots_have_terminal_live_results": true,
  "all_recorded_runtime_fingerprints_match_plan": true,
  "all_recorded_baselines_match_plan": true,
  "missing_slots": [],
  "estimated_reported_inference_usd": 0.654327,
  "reported_usage_covers_all_model_requests": true,
  "rate_card": {
    "schema_version": 1,
    "observed_on": "2026-09-10",
    "source_url": "https://tokenfactory.nebius.com/organization/prices",
    "source_kind": "authenticated official billing price table, observed through browser UI",
    "currency": "USD",
    "unit": "per 1000000 tokens",
    "region_shown": "eu-north1",
    "taxes_included": false,
    "rates": {
      "nvidia/Nemotron-3-Ultra-550b-a55b": {
        "input": 1.0,
        "output": 3.0,
        "valid_from_utc": "2026-06-01",
        "lane": "standard synchronous inference; not Batch"
      }
    },
    "limitations": [
      "Calculations estimate response-reported inference usage only, not an invoice.",
      "Missing usage, taxes, Tavily, Cloud hosting and unverified Sandbox charges are excluded.",
      "Recheck the applicable rates before using this card for a later release."
    ]
  }
}
```
