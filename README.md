# BranchShift

BranchShift is an evidence-first dependency migration agent. It asks NVIDIA
Nemotron on Nebius Token Factory for three distinct migration strategies,
runs each from the same Token Factory Sandbox checkpoint, and selects the
smallest patch that passes deterministic tests.

The current milestone includes a complete offline replay mode so the product
flow, event stream, ranking rules, and interface can be tested without cloud
credentials. Live provider adapters are isolated behind typed boundaries, and
the research/planning layer rejects untrusted sources, uncited strategies, and
model-invented repository paths before any branch can execute.

## Architecture

```text
React control room -> FastAPI + SQLite event ledger
                              |
                 Tavily + Nemotron + Contree
                              |
          baseline -> three branches -> verified winner
```

## Local setup

Requirements: Node.js 20+, pnpm 10+, and Python 3.10+.

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

## Safety boundary

- Only public HTTPS GitHub repository URLs are accepted.
- Untrusted repository code is designed to execute only inside Contree.
- Model output never selects the winner; stored test and patch metrics do.
- Secrets are redacted before provider output reaches the event ledger.
- Live mode will enforce bounded runtime, output, retries, and concurrency.

## Hackathon technology

- **NVIDIA Nemotron on Nebius Token Factory** plans and explains migrations.
- **Token Factory Sandboxes / Contree** branch reproducible filesystem states.
- **Tavily** retrieves allowlisted official migration documentation.
- **FastAPI + React** expose a judge-friendly live audit trail.

See `docs/superpowers/plans/2026-08-31-branchshift-implementation.md` for the
execution-ready build plan.
