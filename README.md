# BranchShift

**MIT licensed** · [License](LICENSE)

Bundled browser assets retain their
[third-party licenses](apps/web/public/third-party-notices.txt).
The pinned runtime candidate is
[`v0.1.0-rc.1`](https://github.com/jsdhwfmax/branchshift-ai/tree/v0.1.0-rc.1);
later packaging changes are documented in the
[asset provenance record](docs/evidence/third-party-assets.md).

[![CI](https://github.com/jsdhwfmax/branchshift-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/jsdhwfmax/branchshift-ai/actions/workflows/ci.yml)

BranchShift is an evidence-first dependency migration agent. It asks NVIDIA
Nemotron on Nebius Token Factory for three distinct migration strategies,
runs each from the same Token Factory Sandbox checkpoint, and selects the
candidate supported by deterministic tests, dependency checks, lint results,
and patch size. The candidate must pass a second execution from the clean
baseline before its patch becomes a verified result.

The live pipeline clones the public repository in a Nebius Sandbox, records
its commit and original tests, retrieves official migration guidance, and asks
an NVIDIA Nemotron model to edit exact source files. Three bounded repair
loops execute independently from the same baseline. Test files and test
configuration remain protected; the final runtime must use Pydantic v2.

An explicitly labelled offline sample is also available. Sample metrics are
illustrative. Five controlled cases now have verified live migration evidence;
broader reliability and public hosting remain under validation.

## Current evaluation evidence

The [latest runtime release verification](docs/evidence/runtime-release-63cf7fd/README.md)
records a real UI-started migration at `63cf7fd`, its downloadable JSON/Markdown
reports and patch, desktop/mobile refresh checks, passing CI and the published
container digest. Public Cloud hosting remains pending.

The [predeclared three-round evaluation](evaluation/series-20260910/README.md)
completed **15/15 qualified live migrations**: validators, configuration,
serialization, parsing and compatibility, each attempted three times at frozen
source/baseline `92c733a`. Every winner preserved the original tests, ran under
Pydantic 2 and passed clean-baseline revalidation. All 45 candidate outcomes
remain visible, including seven failed candidates.

Median ledger duration was **53.022 seconds** and nearest-rank p95
**114.892 seconds**. The collector observed 79 model requests, 275,634 input and
126,231 output tokens, with complete returned-usage coverage. The corresponding
inference estimate is **USD 0.654327**, excluding taxes and other services;
176 returned Sandbox SDK calls are recorded separately from unknown billing.
These five small authored fixtures do not establish general production
migration reliability. Original records, exact patches, fingerprints and all
planned slots are retained in the linked cohort.

The [earlier development record](evaluation/results.md) remains unchanged:
**16 attempts, 9 failures and 7 qualified successes** across changing code/model
settings. It is separate from the frozen series above. See the
[collection and interpretation procedure](docs/evaluation.md).

## Architecture

```text
React control room -> FastAPI + SQLite event ledger
                              |
                 Tavily + Nemotron + Contree
                              |
          baseline -> three branches -> verified winner
```

## Local setup

Tested development environment: Node.js 24, pnpm 11.19, and Python 3.13.

```bash
cp .env.example .env
make install
make check
```

The browser suite serves production assets with local HTTP test data. It checks
desktop/mobile flows, real EventSource reconnects, downloads and selected
accessibility rules without calling live providers:

```bash
pnpm --dir apps/web exec playwright install chromium
pnpm --dir apps/web exec playwright test
```

Start the API and web app in separate terminals:

```bash
make api-dev
make web-dev
```

Open `http://localhost:5173`. The default `BRANCHSHIFT_MODE=mock` runs a
deterministic replay and never calls the network.

The public source repository is
[jsdhwfmax/branchshift-ai](https://github.com/jsdhwfmax/branchshift-ai), and the
controlled Pydantic v1 migration target lives under `fixtures/pydantic-v1-app`.

For live execution, set `BRANCHSHIFT_MODE=live`, `NEBIUS_API_KEY`,
`NEBIUS_PROJECT_ID`, and `TAVILY_API_KEY` in `.env`. Sandbox Beta access must be
enabled for the same Token Factory project. `NEMOTRON_MODEL` selects the exact
NVIDIA model; the run records the model used. The verified configuration uses
`nvidia/Nemotron-3-Ultra-550b-a55b` with `NEMOTRON_ENABLE_THINKING=true`.
Credentials stay in the API.

You can retain a complete live-run summary and any winning patch without
starting the web server:

```bash
.venv/bin/python -m app.cli.live_run --output ./local-evidence
```

For a Python project inside a public monorepo, supply `--project-path` or the
optional **Project directory** field in the live form. Empty input uses the
controlled example directory for this repository and the root for other
repositories. The project must have `pyproject.toml`, installable test
dependencies, and a passing Pydantic v1 baseline.

The UI exports JSON evidence for successful and failed runs. A deterministic
Markdown report is available at `/api/runs/{id}/report?format=markdown`; the CLI
also writes `<id>.md` beside the original JSON and patch. It explains the stored
selection and revalidation, includes failed candidates, and labels missing
usage as unknown. It does not ask a model to invent an explanation. Each record
retains partial branch results, the original test digest, model token counts,
source/config fingerprints, and the final clean-baseline check when available.
Provider token counts are usage evidence, not a total invoice.

Use one API worker per SQLite database. On restart, interrupted runs become
cancelled with their evidence retained. Do not run a separate CLI worker
against an active API database. The CLI output directory provides its own
database by default.

## Safety boundary

- Only public HTTPS GitHub repository URLs are accepted.
- Untrusted repository code is designed to execute only inside Contree.
- Model output never selects the winner; stored test and patch metrics do.
- Secrets are redacted before provider output reaches the event ledger.
- Generated diffs are rejected if they escape the repository, touch undeclared
  files or Git metadata, contain binary data, or exceed configured limits.
- Live mode bounds runtime, source/output size, retries, and concurrency.
- Before dependency installation, a trusted Sandbox check rejects tracked
  checkouts above `MAX_REPOSITORY_BYTES` (50 MiB by default), including files
  outside the chosen project directory. This is a post-checkout acceptance
  gate, not a clone-transfer or complete disk-usage cap.
- HTTP run creation also enforces persistent global and per-client attempt
  quotas, unfinished-run limits and an 8 KiB actual-body cap. Existing evidence
  stays readable after a quota is exhausted. See the deployment runbook for
  proxy configuration and allowance semantics.

[Controlled probes](docs/evidence/security-boundaries.md) verified selected
host-canary boundaries and provider-reported timeouts/output truncation. Public
network egress is allowed. These observations do not establish general
prompt-injection immunity or exhaustive Sandbox isolation.
[Cost and latency evidence](docs/evidence/cost-and-latency.md) separates
response-token estimates, observed SDK calls and unknown billed charges.

See [container deployment](deploy/nebius-endpoint.md) for the prepared
same-origin Python/UI image and persistence requirements. At commit `92c733a`,
[CI](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34443169993) and
[image build, smoke and publication](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34443329138)
passed. The published Linux `amd64` image manifest is anonymously accessible.
Nebius deployment, Cloud persistence and public judge-access checks remain
pending; a published image is not a hosted demo.

## Hackathon technology

- **NVIDIA Nemotron on Nebius Token Factory** plans and explains migrations.
- **Token Factory Sandboxes / Contree** branch reproducible filesystem states.
- **Tavily** retrieves allowlisted official migration documentation.
- **FastAPI + React** expose a judge-friendly live audit trail.

See `docs/superpowers/plans/2026-08-31-branchshift-implementation.md` for the
execution-ready build plan.

## Screenshot

<details>
<summary>Desktop sample replay — expand screenshot</summary>

<img src="docs/images/ui-completed-desktop.png" width="800" alt="BranchShift desktop SAMPLE REPLAY showing illustrative branches, service roles, evidence and patch" />

**SAMPLE REPLAY**: “Metrics, events, and the patch illustrate the workflow using
a fixed sample. No providers were called and no repository migration was
verified in this run.”

[Browser validation and original desktop/mobile screenshots](docs/evidence/ui-browser.md)

</details>
