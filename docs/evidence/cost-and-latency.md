# Cost and latency evidence

Prepared 10 September 2026 from the **16 retained development attempts** in
[attempts.json](../../evaluation/attempts.json). The response-token arithmetic
for the **13 records matching the verified Ultra rate card is USD 0.672222**.
The **actual total charge remains unknown**: three other-model records are
unpriced, historical usage completeness is unverified, and other services and
taxes are excluded. No providers were called to prepare this document.

These are development records across changing implementations and model
settings, including nine failures and seven qualified successes. They are not
a controlled reliability or performance benchmark. The original
[aggregate](../../evaluation/results.md) and raw exports remain unchanged.
The manifest defines this analysis's population; it cannot establish whether
other development experiments were omitted.

## Applicable inference price and arithmetic

The [retained rate card](../../evaluation/pricing-20260910.json) records an
authenticated observation of the official account's
[Prices table](https://tokenfactory.nebius.com/organization/prices) on
10 September 2026, in the displayed `eu-north1` region:

| Exact model ID | Lane | Input / 1 million tokens | Output / 1 million tokens | Valid from | Tax |
| --- | --- | ---: | ---: | --- | --- |
| `nvidia/Nemotron-3-Ultra-550b-a55b` | Standard synchronous inference; **not Batch** | USD 1.00 | USD 3.00 | 2026-06-01 UTC | Excluded |

All 16 retained runs are dated 10 September 2026. For a record with that exact
model ID and nonnegative integer token fields, the calculation is:

```text
reported inference estimate, USD =
    (provider_usage.input_tokens × 1.00
     + provider_usage.output_tokens × 3.00) / 1,000,000
```

The input count comes from the provider response's prompt-token field and the
output count from its completion-token field. The estimate applies no Batch
discount, credit deduction, tax adjustment or separate unverified token price.
Decimal arithmetic is retained to six decimal places for reconciliation;
that precision does not imply invoice accuracy. Recheck the account's
applicable price before using this card for a later release.

| Population | Records | Recorded model requests | Input tokens | Output tokens | Reported-token estimate, USD |
| --- | ---: | ---: | ---: | ---: | --- |
| Exact Ultra match | 13 | 75 | 257,697 | 138,175 | **0.672222**, matched subset only |
| `nvidia/Nemotron-3_5-Lightning`, no matching rate in this card | 3 | 24 | 55,249 | 17,743 | **Unknown** |
| All retained development records | 16 | 99 | 312,946 | 155,918 | **Unknown total** |

Every record has a model ID; none is missing in this population. The three
Lightning records must not inherit the Ultra rate merely because both names
contain Nemotron. A missing or otherwise unmatched model ID in future data
also receives an unknown estimate.

## Per-record reconciliation

`U` means the exact Ultra model above; `L` means the unpriced Lightning model.
Durations are ledger intervals defined in the next section. Links open the
original JSON records, not rewritten cost-enriched copies.

| Run | Case | Outcome | Seconds | Model | Input / output tokens | Reported-token USD |
| --- | --- | --- | ---: | --- | ---: | ---: |
| [f45d8d865b50](../../evaluation/evidence/f45d8d865b50.json) | validators | failed | 44.584 | L | 4,923 / 1,943 | Unknown |
| [e0f5f9a34a45](../../evaluation/evidence/e0f5f9a34a45.json) | validators | failed | 59.974 | L | 24,694 / 9,289 | Unknown |
| [38e8284b4fe3](../../evaluation/evidence/38e8284b4fe3.json) | validators | failed | 56.190 | L | 25,632 / 6,511 | Unknown |
| [866e14413018](../../evaluation/evidence/866e14413018.json) | validators | failed | 29.759 | U | 0 / 0 | 0.000000† |
| [c4db91327858](../../evaluation/evidence/c4db91327858.json) | validators | failed | 68.983 | U | 25,860 / 7,561 | 0.048543 |
| [88c20bab4e91](../../evaluation/evidence/88c20bab4e91.json) | validators | failed | 34.793 | U | 7,350 / 1,589 | 0.012117 |
| [23c4e360b67a](../../evaluation/evidence/23c4e360b67a.json) | validators | failed | 30.214 | U | 0 / 0 | 0.000000† |
| [65d80241c3dc](../../evaluation/evidence/65d80241c3dc.json) | validators | failed | 106.409 | U | 21,690 / 58,335 | 0.196695 |
| [1d3583ee632a](../../evaluation/evidence/1d3583ee632a.json) | validators | failed | 69.660 | U | 43,769 / 8,132 | 0.068165 |
| [6d863a18d814](../../evaluation/evidence/6d863a18d814.json) | validators | completed | 89.343 | U | 35,389 / 15,952 | 0.083245 |
| [83489c0de0de](../../evaluation/evidence/83489c0de0de.json) | validators | completed | 77.417 | U | 34,076 / 12,274 | 0.070898 |
| [aedb7bf272f4](../../evaluation/evidence/aedb7bf272f4.json) | validators | completed | 89.912 | U | 24,663 / 18,472 | 0.080079 |
| [113e13ad8413](../../evaluation/evidence/113e13ad8413.json) | config | completed | 59.695 | U | 19,804 / 5,023 | 0.034873 |
| [714229fb2814](../../evaluation/evidence/714229fb2814.json) | serialization | completed | 48.199 | U | 19,834 / 5,039 | 0.034951 |
| [5b124a9d5dee](../../evaluation/evidence/5b124a9d5dee.json) | parsing | completed | 49.323 | U | 12,392 / 2,329 | 0.019379 |
| [fe86c430aa32](../../evaluation/evidence/fe86c430aa32.json) | compatibility | completed | 57.627 | U | 12,870 / 3,469 | 0.023277 |

† These two records explicitly retain zero requests and zero token totals.
The zero shown is only the formula's result on those fields. It is **not** a
claim that the run, Sandbox work, or account charge was zero. Missing or
unreported service charges have not been filled with zero.

The seven completed Ultra records contribute USD 0.346702; the six failed
Ultra records contribute USD 0.325520, including the two recorded-zero rows.
Keeping failures in the subtotal avoids presenting only the cost of successful
attempts. This still excludes the three failed Lightning records.

## Historical usage completeness is unknown

All 16 historical `provider_usage` objects contain only `requests`,
`input_tokens` and `output_tokens`. None has `model_usage_version` or
`responses_with_usage`. Their presence as numeric totals does not establish
that every attempted model request returned usage, that timeouts were free,
or that provider-side processing stopped when a local request failed.

The estimate therefore describes **recorded response tokens only**, not a
complete inference invoice or a verified lower bound on final billed USD.
Credits, invoice rounding, unreported usage and account-specific adjustments
could change the billed amount. Do not retroactively add completeness markers
or observed-zero Sandbox counts to these historical exports.

## Observed latency

For each terminal record:

```text
ledger duration, seconds = updated_at − created_at
```

This interval includes the run's queue time and final ledger writes. It is not
isolated model latency, GPU execution time, or browser-perceived response time.
Statistics below are calculated from the original timestamps and then rounded
to three decimals. The nearest-rank p95 is the value at sorted rank
`ceil(0.95 × n)`, with ranks starting at one.

| Population | n | Median seconds | p95 seconds | Minimum seconds | Maximum seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| All retained terminal live attempts | 16 | **58.661** | **106.409** | 29.759 | 106.409 |
| Completed attempts | 7 | 59.695 | 89.912 | 48.199 | 89.912 |
| Failed attempts | 9 | 56.190 | 106.409 | 29.759 | 106.409 |

At these sample sizes p95 is the maximum observation in each group. It is a
description of retained development work, not a tail-latency service guarantee.
Some attempts failed early; the completed-only row is conditional on success.
The run intervals overlap in places, so summing durations is not elapsed wall
time for the development session or a hosting bill.

These runs do not establish a single-strategy versus three-strategy cost or
latency comparison. Shared baseline/research work and concurrent branches
prevent dividing total run usage by three or summing branch durations to infer
that comparison.

## Sandbox usage is a separate measurement

The historical records have no `sandbox_usage_version` or Sandbox counters.
Their SDK call counts and billed operation totals remain **unknown**.

The new [adapter instrumentation](../../services/api/app/providers/contree.py)
uses version 1 counters for observed invocations of `images.use`, state `run`
and state `read`, with attempted/completed/failed/cancelled outcomes. A returned
nonzero shell exit is a completed SDK call and is counted separately from a
zero exit; it is not a successful migration. Failed or cancelled calls have
an uncertain remote outcome. For a settled terminal snapshot, attempted must
equal completed + failed + cancelled, both for each operation and in total.

Those counters are **adapter SDK invocations**, not internal SDK HTTP requests,
polling requests, separate shell commands, or billable Sandbox operations.
Producing a child checkpoint via `run` is not counted again as an invented
spawn/fork operation. File writes and metrics commands inside that invocation
are not additional SDK calls.

The official [operation-status API](https://docs.tokenfactory.nebius.com/api-reference/sandboxes/operations/get-an-operation-status.md)
and [published OpenAPI](https://eu-north.nebius.computer/static/api.yaml) describe
`cost` as a float named “Operation cost” without establishing a currency or
conversion unit. A raw `cost` value must not be relabeled as USD, credits,
seconds or a token count. The inspected SDK surfaces also differ: installed
`contree-sdk==0.4.0.dev5` has an optional result cost field, while the reviewed
[newer source revision](https://github.com/nebius/contree-sdk/blob/38d973120ecdb8e459ab7ee375704c7aef54d035/contree_sdk/sdk/objects/image_like/result.py#L17)
sets result cost to `None`. Neither proves a charge amount for these runs.

The [Sandbox Beta overview](https://docs.tokenfactory.nebius.com/sandboxes/overview)
does not establish a free-use promise. Beta access or a missing charge field
does not establish zero cost. Sandbox pricing/units, any applicable free tier,
and the actual account charge remain unverified here.

| Excluded item | Treatment |
| --- | --- |
| Unmatched-model or missing inference usage | Unknown; no substitute rate or zero |
| Sandbox operations and billing | Unknown units/charges; SDK calls kept separate |
| Tavily retrieval | Not priced in this analysis; unknown charge |
| AI Cloud runtime, disk, network, backups and registry | Not included; separate deployment estimate and actual billing required |
| Taxes and credit deductions | Excluded; not inferred from the rate card |

## Next declared 15-run series: collection method, results pending

**No result from the next series is included in this document.** At preparation
time it had not begun. The next batch is intended to cover the five declared
cases for three rounds, using the [series runner](../../evaluation/run_evaluation.py)
and [series summarizer](../../services/api/app/cli/series.py). Its actual results
must be appended as a separate dated cohort, not merged into a claim that these
16 development attempts used a frozen implementation.

1. Retain the predeclared 15 case/round slots, exact public baseline commit,
   model ID, orchestrator content digest, runtime-config digest and applicable
   price card before starting. Preserve failures and interrupted attempts.
   Never replace a failed slot silently with a successful retry.
2. Retain the original per-run summary/report and patch, ledger timestamps,
   test-contract and revalidation evidence, and the complete usage object.
   Verify every planned slot has a terminal live record; list missing slots.
3. For inference version 1, record attempted `requests`,
   `responses_with_usage`, input and output totals. Only label observed usage
   coverage complete when the version is present, counts are valid, and
   `requests == responses_with_usage`. An absent marker or mismatch requires
   an unknown/incomplete label, even when some token totals are available.
   Complete response coverage still does not make the estimate an invoice.
4. Preserve Sandbox version 1 outcome counters and check the settled-count
   identities above. Do not derive billed operations or currency from them.
   If native operation cost is later captured, retain its raw value and unit
   uncertainty until an authoritative billing mapping is verified.
5. Recompute exact-model token estimates, unconditional latency with failures,
   success-conditioned latency and per-case sample sizes. Report the rate-card
   source, date, lane, currency and tax exclusion beside the numbers. Leave
   unmatched or missing costs unknown and retain the original data unchanged.
6. The runner's estimate threshold is checked **between runs**, and missing
   usage stops further scheduled work for review. It is not a hard provider
   spending cap: a run already underway can exceed the remaining estimate,
   and excluded services remain outside it. No new-series estimate or total
   is asserted until its actual retained results exist.

## Local validation and source identity

Local checks loaded every manifest path, verified 16 unique terminal live run
IDs, nonnegative integer retained token counts and nonnegative timestamp
intervals, matched model IDs exactly, and recomputed all table values using
decimal arithmetic. All 16 lacked the new completeness and Sandbox-version
markers. The inference subtotal and latency statistics were checked against
the original records; no provider requests or aggregate rewrites were made.

| Input | SHA-256 at preparation |
| --- | --- |
| `evaluation/attempts.json` | `d7203ace90d52efef8eb98314a550336f6ee8a51241f48ebe4da40b31fc03db9` |
| `evaluation/pricing-20260910.json` | `fab9d6e2d95a9e75bed87ea1f59a26ed767d79a945f336e32d5a63da2b48f617` |
