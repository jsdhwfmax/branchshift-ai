# Three complete rounds of live migration evaluation

On 10 September 2026, the predeclared **five-case × three-round** series
finished with **15/15 qualified migrations (100% in these controlled cases)**.
All 15 planned slots were attempted once and retained. There were no replaced
or omitted failed run slots; the 45 candidate results include **38 passes and
7 failures**. This is a small authored-fixture benchmark, not a production
reliability estimate or proof that arbitrary migrations succeed.

The [series plan](series-plan.json) was written before execution. Its public
baseline and runtime source revision are
[`92c733a1338cc7abdbcf04ca00be363158fd126c`](https://github.com/jsdhwfmax/branchshift-ai/tree/92c733a1338cc7abdbcf04ca00be363158fd126c).
The runtime content digest and configuration digest match the declaration in
every record. Source was frozen while the series ran. Git dirty status remains
true because local documentation/media drafts were present; it is not silently
rewritten to a clean checkout. Subsequent implementation changes are outside this
cohort and do not retroactively change its tested runtime identity.

The exact model is `nvidia/Nemotron-3-Ultra-550b-a55b`, with thinking enabled.
Each qualified winner preserves the original test contract, passes with
Pydantic 2 and `pip check`, and repeats those checks after applying the exact
patch to the clean baseline. The case counts remain 13/5/4/4/4 original tests.
Fourteen runs retain three distinct candidate child checkpoints. In round 2
serialization, the minimal proposal failed safety validation before execution;
the two other candidates and the selected patch's clean revalidation passed.
That run is not described as three executed child states.

| Case | Qualified / attempted | Median ledger duration | Original summaries, rounds 1–3 |
| --- | ---: | ---: | --- |
| validators | 3/3 | 108.534 s | [3c96a45e7a8b](round-01/validators/3c96a45e7a8b.json) · [73347c34a2ef](round-02/validators/73347c34a2ef.json) · [b93c8df744ac](round-03/validators/b93c8df744ac.json) |
| config | 3/3 | 64.845 s | [2e86cf16dfc0](round-01/config/2e86cf16dfc0.json) · [f87a0a787413](round-02/config/f87a0a787413.json) · [ee4ce9911531](round-03/config/ee4ce9911531.json) |
| serialization | 3/3 | 49.585 s | [eea3304afbe6](round-01/serialization/eea3304afbe6.json) · [6bc43693144a](round-02/serialization/6bc43693144a.json) · [f3f3b10e5df1](round-03/serialization/f3f3b10e5df1.json) |
| parsing | 3/3 | 48.271 s | [b6475ac669f8](round-01/parsing/b6475ac669f8.json) · [67cfd318e689](round-02/parsing/67cfd318e689.json) · [2d501a3e059f](round-03/parsing/2d501a3e059f.json) |
| compatibility | 3/3 | 53.022 s | [97b310dcbde7](round-01/compatibility/97b310dcbde7.json) · [e6dd367c1436](round-02/compatibility/e6dd367c1436.json) · [b249a85a9f78](round-03/compatibility/b249a85a9f78.json) |

## Timing, usage and estimated inference cost

- Median ledger duration: **53.022 seconds**; nearest-rank p95:
  **114.892 seconds**. These intervals include queue time and final ledger writes.
  With 15 observations, this p95 is the maximum; it is not a latency guarantee.
- Model requests: **79**. All 79 returned valid token-usage fields in the
  versioned collector: **275,634 input + 126,231 output tokens**.
- Reported-token inference estimate: **USD 0.654327**, using standard
  synchronous rates of USD 1/input million and USD 3/output million from the
  [observed rate card](../pricing-20260910.json). It is not an invoice and excludes
  taxes, credit adjustments, Tavily, hosting and unknown Sandbox charges.
- Sandbox adapter SDK calls: **176 attempted, 176 returned, 0 exceptions,
  0 cancellations**. All records have balanced versioned counters. These count
  `images.use`, state `run` and state `read`; they exclude SDK polling/retries
  and do not establish billable operation counts. A returned SDK call can still
  contain failed workload/test evidence.

See the [generated report](results.md), [machine-readable results](results.json)
and [complete slot manifest](attempts.json). Aggregation reads retained exports;
it does not replay patches or independently authenticate provider telemetry.
The live pipeline performed the revalidations recorded in those exports.

## Retained evidence and reproduction

The 15 original summaries and their 15 standalone patches were copied
byte-for-byte alongside the original plan, manifest and generated reports.
Each standalone patch matches both its summary patch and clean-revalidation
patch. The [collection receipt](collection-verification.json) lists SHA-256
values, verifies unique runs/slots, and records the scoped credential check.
Private SQLite databases and credentials are not included.

To collect a **new** series, use a fresh output directory and its own predeclared
public commit. Do not overwrite this cohort or silently retry an uncertain slot:

```sh
.venv/bin/python evaluation/run_evaluation.py \
  --expected-commit FULL_PUBLIC_COMMIT_SHA \
  --output ./local-evidence/new-three-rounds \
  --rounds 3 --max-estimated-inference-usd 3.0
```

This command uses configured real providers. The estimate ceiling is checked
between runs and is not a hard spending cap or a limit on excluded services.
The [16 earlier development attempts](../results.md) remain a separate, unchanged
cohort with nine failed runs. They are not combined with these 15 into a
single fixed-configuration reliability rate.
