# BranchShift

**MIT licensed** · [License](LICENSE)

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
illustrative. Live reliability, five-case evaluation and public hosting remain
under validation; this repository does not claim that every migration succeeds.

## Current evaluation evidence

The [retained development record](evaluation/results.md) contains **12
autonomous live attempts: 9 failures and 3 qualified successes**. Code and
model settings changed during the earlier attempts. The latest three runs
passed consecutively with the same baseline, model, source digest and runtime
configuration; each winner preserved and passed all 13 original tests under
Pydantic 2 and passed clean-baseline revalidation.

This covers **one controlled fixture**, not five independent migration cases
or a general reliability rate. Four additional fixture baselines pass locally;
their public-source and live migration evaluation remains pending. Original
JSON records, failure outcomes and provenance are retained in
[evaluation/evidence](evaluation/evidence), with the
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
NVIDIA model; the run records the model used. Credentials stay in the API.

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

The UI exports JSON evidence for successful and failed runs. Each record
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

See [container deployment](deploy/nebius-endpoint.md) for the prepared
same-origin Python/UI image and persistence requirements. A Docker build,
public deployment, and judge-access checks are still required before claiming
a hosted demo.

## Hackathon technology

- **NVIDIA Nemotron on Nebius Token Factory** plans and explains migrations.
- **Token Factory Sandboxes / Contree** branch reproducible filesystem states.
- **Tavily** retrieves allowlisted official migration documentation.
- **FastAPI + React** expose a judge-friendly live audit trail.

See `docs/superpowers/plans/2026-08-31-branchshift-implementation.md` for the
execution-ready build plan.
