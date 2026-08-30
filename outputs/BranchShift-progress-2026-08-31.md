# BranchShift progress — 31 August 2026

## Working now

- Git-initialized pnpm/Python monorepo with MIT license and one-command checks.
- FastAPI service with public-GitHub URL validation, SQLite persistence,
  append-only events, state transitions, SSE, and patch download.
- Deterministic three-branch replay: all strategies execute concurrently from
  one conceptual checkpoint and the evaluator selects the smallest fully
  passing patch.
- Typed Nebius inference, Tavily, and Contree provider adapters. The Contree
  adapter supports both the current documented transport-injection API and the
  constructor still present in the newest PyPI pre-release.
- A grounded live research/planning boundary: only allowlisted official sources
  survive retrieval, every Nemotron strategy must cite retained evidence, and
  generated plans can reference only repository files observed by BranchShift.
- A unified-diff safety gate that rejects path traversal, Git metadata changes,
  binary content, oversized patches, duplicate file sections, and files that
  were not declared by the selected migration strategy.
- Judge-facing React control room with desktop and mobile layouts, keyboard
  focus treatment, reduced-motion handling, live event ledger, evidence table,
  citations, and unified-diff viewer.
- A real Pydantic 1.10 fixture with thirteen passing baseline tests covering
  legacy validators, root validators, config, aliases, `parse_obj`, `parse_raw`,
  and `.dict()`.

## Verification evidence

- API: 30 tests passing.
- Pydantic v1 fixture: 13 tests passing in its own pinned environment.
- Web: 2 component tests passing; TypeScript clean; production Vite build clean.
- Python: Ruff clean; strict mypy clean across 22 source files.
- Browser: complete repository-to-winner replay confirmed; mobile viewport
  `390px`, document width `390px` (no horizontal overflow).
- Public source: `https://github.com/jsdhwfmax/branchshift-ai`; GitHub Actions CI
  passed the same full quality gate on a clean Ubuntu runner.

Run the full local gate with:

```bash
make check
```

Run the app with:

```bash
make api-dev
make web-dev
```

## Live integration status

- Tavily is configured locally in the gitignored `.env`; a real request passed
  through the allowlist and retained five official Pydantic documentation pages.
- The official hackathon Token Factory credit request was submitted with the
  event activation code; Nebius confirmed that a personal promo code will be
  delivered by email.
- Nebius inference and Contree remain intentionally gated until the promo code
  is redeemed and an API key with Sandbox access exists. Token Factory currently
  asks for billing details and a card before it exposes the API-key page; no
  address or payment information was guessed or entered.

## Next actions

1. Redeem the emailed hackathon promo code and create a Nebius Token Factory
   API key with Sandbox access; store it only in the local `.env`.
2. Run `.venv/bin/python -m app.cli.sandbox_spike` and save redacted evidence.
3. Wire the live run manager to Tavily retrieval, schema-valid Nemotron plans,
   bounded patch repair, and the real three-way Contree execution.
4. Publish the controlled fixture to the eventual public GitHub repository,
   then replace the homepage replay URL.
