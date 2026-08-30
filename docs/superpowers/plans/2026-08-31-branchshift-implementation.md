# BranchShift implementation plan

**Goal:** Deliver a public, judge-ready Coding & Agentic Engineering submission that uses NVIDIA Nemotron on Nebius Token Factory to plan a Pydantic v1-to-v2 migration, executes competing strategies in branched Token Factory Sandboxes, and returns the smallest verified winning patch with an auditable report.

**Approach:** Build a small monorepo with a React/Vite interface and a FastAPI orchestration service. The backend will use Nebius Token Factory for Nemotron inference, Tavily for official migration-document retrieval, and the Contree SDK for isolated, checkpointed execution. Deterministic tests and metrics—not an LLM opinion—will decide the winning branch; Nemotron will explain the evidence and produce the migration plan.

**Affected areas:** Repository bootstrap, React UI, FastAPI API, Nebius and Tavily providers, Contree sandbox orchestration, SQLite run state, migration fixtures, security controls, Nebius Serverless deployment, evaluation evidence, and Devpost submission assets.

## Planning basis

### Confirmed requirements

- The Devpost registration is complete; the page displays “Thanks for registering!”.
- The project is an individual submission in the Coding & Agentic Engineering track.
- Working name: **BranchShift**.
- MVP migration: **Pydantic v1 to Pydantic v2** for public GitHub repositories.
- Each run must create multiple strategies from a shared checkpoint, execute them in Token Factory Sandboxes, test them, compare evidence, and return one winning patch.
- The project must make runtime calls to Nebius Token Factory and an NVIDIA open model.
- The final repository must be public, include an open-source license, setup instructions, a working demo, and an English video no longer than three minutes.
- Submission deadline: **31 October 2026 at 04:00 AEDT**. Internal submission target: **29 October 2026 at 18:00 AEDT**.

### Assumptions and scope boundaries

- The current workspace is empty and is not yet a Git repository, so all paths below are new.
- Local tools currently available are Node.js 24, pnpm 11, and Python 3.9. Docker and `uv` are not installed; the plan uses `venv`/`pip` locally and GitHub Actions to build the deployment image.
- The MVP accepts public `https://github.com/...` repositories only. It does not request GitHub OAuth, push branches, or open pull requests.
- The first reliable demo uses a repository fixture owned by this project. Arbitrary public repositories remain an experimental feature until the fixture path passes consistently.
- SQLite is sufficient for one public demo instance and can be replaced later without changing API contracts.
- The UI and API are packaged into one container: Vite builds static assets, and FastAPI serves both the SPA and `/api/*` routes.
- External account creation, API-key creation, GitHub repository creation, and final Devpost submission require separate user approval during implementation.

## Target architecture and contracts

```text
React/Vite SPA
  ├─ POST /api/runs
  ├─ GET  /api/runs/{run_id}
  ├─ GET  /api/runs/{run_id}/events      (Server-Sent Events)
  └─ GET  /api/runs/{run_id}/patch
              │
              ▼
FastAPI orchestrator + SQLite event store
  ├─ Tavily: retrieve official migration guidance
  ├─ Nemotron: inspect, plan, generate candidate patches, explain result
  └─ Contree SDK / Token Factory Sandboxes
       ├─ baseline checkpoint
       ├─ minimal-change branch
       ├─ compatibility branch
       └─ refactor branch
              │
              ▼
Deterministic evaluator
  ├─ tests collected / passed / failed
  ├─ `pip check`
  ├─ lint findings
  ├─ changed lines and files
  ├─ elapsed time
  └─ patch applicability
```

Core API shapes:

```python
class CreateRunRequest(BaseModel):
    repo_url: HttpUrl
    target: Literal["pydantic-v2"] = "pydantic-v2"

class MigrationStrategy(BaseModel):
    id: Literal["minimal", "compatibility", "refactor"]
    title: str
    rationale: str
    ordered_steps: list[str]
    source_urls: list[HttpUrl]

class BranchResult(BaseModel):
    strategy_id: str
    status: Literal["passed", "failed", "timed_out"]
    tests_collected: int
    tests_passed: int
    tests_failed: int
    pip_check_passed: bool
    lint_findings: int
    changed_files: int
    changed_lines: int
    elapsed_seconds: float
    patch: str | None
```

Winner selection is deterministic:

1. Reject branches whose patch cannot be reapplied to the baseline checkpoint.
2. Prefer branches with `pip check` success and zero failed tests.
3. If none fully pass, rank by highest test pass ratio and clearly label the run unsuccessful.
4. Break ties by fewer lint findings, then fewer changed lines, then shorter execution time.
5. Ask Nemotron to explain the selected result from stored metrics; it cannot override the ranking.

## Ordered implementation tasks

### Task 1: Create a reproducible monorepo and local quality gate

**Outcome:** A Git-initialized workspace with installable web and API packages, shared commands, environment documentation, and a one-command check.

**Files:**

- Create: `.gitignore`
- Create: `.env.example`
- Create: `LICENSE`
- Create: `README.md`
- Create: `Makefile`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `apps/web/**`
- Create: `services/api/pyproject.toml`
- Create: `services/api/app/__init__.py`
- Create: `services/api/tests/test_smoke.py`

- [ ] Run `git init` and set the default branch to `main`; confirm `git branch --show-current` prints `main` after the first commit is created.
- [ ] Scaffold the UI with `pnpm create vite apps/web --template react-ts` and add React Router, Vitest, Testing Library, Tailwind CSS, and Playwright as development dependencies.
- [ ] Create the FastAPI package in `services/api` with Python `>=3.9`, plus FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, aiosqlite, httpx, OpenAI, `contree-sdk`, and `tavily-python` dependencies. Add pytest, pytest-asyncio, respx, ruff, and mypy as development dependencies.
- [ ] Add root scripts for `web:dev`, `web:test`, `api:dev`, `api:test`, `lint`, and `check`; have `make check` run frontend tests/lint/build and backend tests/ruff/mypy.
- [ ] Document every required environment variable in `.env.example` without real values: `NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID`, `NEBIUS_BASE_URL`, `NEMOTRON_MODEL`, `TAVILY_API_KEY`, `CONTREE_API_URL`, `DATABASE_URL`, `RUN_TIMEOUT_SECONDS`, and `MAX_CONCURRENT_RUNS`.
- [ ] Add an MIT license and a README skeleton containing problem, architecture, local setup, safety, and hackathon-technology sections.
- [ ] Run `python3 -m venv .venv && .venv/bin/python -m pip install -U pip && .venv/bin/python -m pip install -e 'services/api[dev]'`; confirm package installation completes without dependency conflicts.
- [ ] Run `pnpm install && make check`; confirm the smoke test, frontend test, type checks, lint checks, and production web build all pass.

### Task 2: Define domain models, persistence, and event semantics

**Outcome:** Stable run/branch contracts and a SQLite-backed state machine that survives browser refreshes and exposes an ordered audit trail.

**Files:**

- Create: `services/api/app/domain/models.py`
- Create: `services/api/app/domain/events.py`
- Create: `services/api/app/storage/database.py`
- Create: `services/api/app/storage/repositories.py`
- Create: `services/api/app/config.py`
- Test: `services/api/tests/domain/test_models.py`
- Test: `services/api/tests/storage/test_repositories.py`

- [ ] Define `RunStatus`, `BranchStatus`, `CreateRunRequest`, `MigrationStrategy`, `BranchResult`, `RunSummary`, and `RunEvent` with explicit enums and UTC timestamps.
- [ ] Define permitted run transitions: `queued → preparing → planning → branching → evaluating → completed|failed|cancelled`; reject backwards or skipped transitions.
- [ ] Persist runs, strategies, branch metrics, redacted logs, patches, citations, and append-only events using SQLAlchemy 2.
- [ ] Ensure patches and logs have byte limits; store a truncation flag instead of silently cutting evidence.
- [ ] Add repository methods `create_run`, `append_event`, `set_run_status`, `save_strategy`, `save_branch_result`, and `get_run_summary`.
- [ ] Test valid and invalid state transitions, ordered events, restart persistence, and patch/log truncation.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/domain services/api/tests/storage -q`; confirm all tests pass and a temporary SQLite database is removed after each test.

### Task 3: Add mockable Nebius, Tavily, and Sandbox provider boundaries

**Outcome:** External integrations are isolated behind typed interfaces, with health checks that prove configuration without leaking credentials.

**Files:**

- Create: `services/api/app/providers/base.py`
- Create: `services/api/app/providers/nebius.py`
- Create: `services/api/app/providers/tavily.py`
- Create: `services/api/app/providers/contree.py`
- Create: `services/api/app/providers/redaction.py`
- Test: `services/api/tests/providers/test_nebius.py`
- Test: `services/api/tests/providers/test_tavily.py`
- Test: `services/api/tests/providers/test_contree.py`
- Test: `services/api/tests/providers/test_redaction.py`

- [ ] Define protocols for model completion, document search, sandbox checkpoint creation, branching, command execution, file reads, and patch export.
- [ ] Configure the OpenAI Python client with the Nebius Token Factory base URL and `NEMOTRON_MODEL`; require structured JSON responses validated through Pydantic.
- [ ] Implement Tavily search with a domain allowlist for official Pydantic, Python, and dependency documentation; retain title, URL, and a short paraphrased evidence excerpt.
- [ ] Wrap the Contree SDK so orchestration code never depends on raw SDK response shapes. Represent a checkpoint with an opaque `checkpoint_id` only.
- [ ] Redact bearer tokens, common secret formats, and configured environment values before logs or events are persisted.
- [ ] Add provider fakes that replay deterministic fixtures and never call the network during unit tests.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/providers -q`; confirm all provider tests use mocks and captured output contains no test secrets.

### Task 4: Prove the Token Factory Sandbox branching primitive

**Outcome:** A command-line technical spike can create one baseline checkpoint, fork three branches, run different commands, and export isolated results.

**Files:**

- Create: `services/api/app/cli/sandbox_spike.py`
- Create: `services/api/tests/integration/test_contree_branching.py`
- Create: `docs/evidence/sandbox-spike.md`

- [ ] Implement `python -m app.cli.sandbox_spike` to import or select a small Python OCI image, create `/workspace/marker.txt`, checkpoint it, and fork `minimal`, `compatibility`, and `refactor` branches.
- [ ] Write a distinct marker in each branch, read it back, and confirm no branch sees another branch’s marker.
- [ ] Record operation IDs, checkpoint IDs, duration, and redacted command output in `docs/evidence/sandbox-spike.md`.
- [ ] Mark the integration test with `@pytest.mark.nebius` so the normal suite remains offline.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/integration/test_contree_branching.py -m nebius -q`; confirm three isolated branches complete and the test exits zero.
- [ ] Stop and reassess the track only if branching cannot be demonstrated after two focused days; do not build a local-container substitute that would weaken the required Nebius story.

### Task 5: Build a deterministic Pydantic migration fixture and baseline runner

**Outcome:** BranchShift can clone a controlled repository into a Sandbox, detect its Python test command, run a Pydantic v1 baseline, and preserve a checkpoint for migration branches.

**Files:**

- Create: `fixtures/pydantic-v1-app/LICENSE`
- Create: `fixtures/pydantic-v1-app/pyproject.toml`
- Create: `fixtures/pydantic-v1-app/src/sample_app/models.py`
- Create: `fixtures/pydantic-v1-app/src/sample_app/api.py`
- Create: `fixtures/pydantic-v1-app/tests/test_models.py`
- Create: `fixtures/pydantic-v1-app/tests/test_api.py`
- Create: `services/api/app/orchestrator/repository.py`
- Create: `services/api/app/orchestrator/baseline.py`
- Test: `services/api/tests/orchestrator/test_repository.py`
- Test: `services/api/tests/orchestrator/test_baseline.py`

- [ ] Create an MIT-licensed fixture that uses Pydantic v1 validators, `parse_obj`, `.dict()`, legacy config, and serialization behavior covered by at least twelve tests.
- [ ] Validate repository URLs with `urllib.parse`: allow only HTTPS GitHub repository URLs, reject credentials, fragments, non-default ports, private-network hosts, and repositories above a configured archive-size limit.
- [ ] Clone inside the Sandbox at a pinned commit. Never clone or execute repository code on the host running FastAPI.
- [ ] Detect `pytest` from `pyproject.toml`; for the MVP, fail with a clear unsupported-project message when no Python/pytest configuration exists.
- [ ] Install dependencies and run the baseline with explicit time, CPU/memory, network, and output limits. Preserve the passing state as the shared checkpoint.
- [ ] Test malicious URLs, unsupported repositories, timeouts, output truncation, a passing baseline, and a failing baseline.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/orchestrator/test_repository.py services/api/tests/orchestrator/test_baseline.py -q`; confirm all rejection cases are deterministic and the fixture collects at least twelve tests.

### Task 6: Produce cited, structured migration strategies with Nemotron

**Outcome:** Given repository evidence and official documentation, Nemotron returns exactly three valid, distinct migration strategies with citations.

**Files:**

- Create: `services/api/app/orchestrator/research.py`
- Create: `services/api/app/orchestrator/planner.py`
- Create: `services/api/app/prompts/planner.md`
- Create: `services/api/app/prompts/repair.md`
- Test: `services/api/tests/orchestrator/test_research.py`
- Test: `services/api/tests/orchestrator/test_planner.py`
- Fixture: `services/api/tests/fixtures/nemotron/planner_response.json`

- [ ] Query Tavily at runtime for Pydantic’s official migration guide and API references, then discard results outside the allowlist.
- [ ] Inspect only bounded repository artifacts: dependency manifests, Python filenames, import/use matches, and baseline-test summary. Do not send secrets or the entire repository blindly.
- [ ] Ask Nemotron for `minimal`, `compatibility`, and `refactor` strategies using the `MigrationStrategy` schema.
- [ ] Require each strategy to cite at least one retained official source and identify concrete files or symbol patterns to change.
- [ ] Reject duplicate strategies, unknown files, uncited claims, invalid JSON, or more than the configured token budget; retry once with validation feedback.
- [ ] Test successful planning, malformed JSON, hallucinated paths, duplicate strategy IDs, missing citations, and retry exhaustion.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/orchestrator/test_research.py services/api/tests/orchestrator/test_planner.py -q`; confirm all invalid responses fail closed.

### Task 7: Execute and repair three migration branches in parallel

**Outcome:** Each strategy receives its own Sandbox branch, generates a patch through a bounded Nemotron loop, applies it, and runs validation independently.

**Files:**

- Create: `services/api/app/orchestrator/patches.py`
- Create: `services/api/app/orchestrator/branch_runner.py`
- Create: `services/api/app/orchestrator/run_manager.py`
- Test: `services/api/tests/orchestrator/test_patches.py`
- Test: `services/api/tests/orchestrator/test_branch_runner.py`
- Test: `services/api/tests/orchestrator/test_run_manager.py`

- [ ] Ask Nemotron to return a unified diff only; run `git apply --check` before applying it inside the Sandbox.
- [ ] On an invalid patch or failed test run, return bounded diagnostics to Nemotron and allow at most three repair attempts per branch.
- [ ] Run `pytest`, `pip check`, and Ruff after every final patch; collect exact exit codes and counts without letting repository text alter host-side instructions.
- [ ] Use `asyncio.TaskGroup` or an equivalent Python 3.9-compatible gather/cancellation pattern with a semaphore so three branches execute concurrently while respecting `MAX_CONCURRENT_RUNS`.
- [ ] Cancel sibling work only for a run-level fatal error; one failed strategy must not erase successful branch evidence.
- [ ] Persist an event for every state change so the UI can show preparation, patch attempts, tests, and completion.
- [ ] Test patch path traversal, binary patches, oversized diffs, retry exhaustion, one-branch failure, full cancellation, and three-branch success.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/orchestrator/test_patches.py services/api/tests/orchestrator/test_branch_runner.py services/api/tests/orchestrator/test_run_manager.py -q`; confirm mocked branches overlap in time and preserve independent results.

### Task 8: Rank results deterministically and generate the evidence report

**Outcome:** BranchShift selects a winner from test evidence, exports a re-applicable patch, and generates a cited report that matches the stored metrics.

**Files:**

- Create: `services/api/app/orchestrator/evaluator.py`
- Create: `services/api/app/orchestrator/report.py`
- Create: `services/api/app/prompts/report.md`
- Test: `services/api/tests/orchestrator/test_evaluator.py`
- Test: `services/api/tests/orchestrator/test_report.py`

- [ ] Implement the ranking rules from this plan as pure functions with no model calls.
- [ ] Reapply the candidate patch to a fresh copy of the baseline checkpoint and rerun the winning validation command before marking a run complete.
- [ ] Have Nemotron produce a short explanation from an immutable metrics payload and official citations; validate that every number in the explanation occurs in the payload.
- [ ] Export `winner.patch`, `report.json`, and `report.md`; include failed-branch evidence rather than hiding it.
- [ ] Test all-pass ties, partial failures, complete failure, patch-reapply failure, metric mismatch in the explanation, and deterministic ordering.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/orchestrator/test_evaluator.py services/api/tests/orchestrator/test_report.py -q`; confirm repeated evaluations of the same inputs produce byte-identical JSON.

### Task 9: Expose the orchestration API and live event stream

**Outcome:** The UI can start, follow, inspect, and download a migration run through documented HTTP endpoints.

**Files:**

- Create: `services/api/app/main.py`
- Create: `services/api/app/api/runs.py`
- Create: `services/api/app/api/health.py`
- Create: `services/api/app/api/sse.py`
- Test: `services/api/tests/api/test_runs.py`
- Test: `services/api/tests/api/test_sse.py`
- Test: `services/api/tests/api/test_health.py`

- [ ] Implement `POST /api/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/events`, `GET /api/runs/{id}/patch`, and `GET /api/health/integrations`.
- [ ] Return `202 Accepted` immediately from run creation and execute orchestration in a bounded background task owned by the process.
- [ ] Resume SSE clients from `Last-Event-ID`, emit heartbeats, and end the stream after a terminal event.
- [ ] Add per-IP run limits, global concurrency limits, request-size limits, and explicit error codes for unsupported repositories and exhausted demo quota.
- [ ] Make the health endpoint report only configured/available booleans and latency; never return model credentials or raw provider errors.
- [ ] Generate an OpenAPI snapshot at `docs/evidence/openapi.json` and fail tests when endpoint contracts change unintentionally.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/api -q`; confirm a mocked end-to-end run reaches `completed`, streams ordered events, and downloads the expected patch.

### Task 10: Build the judge-facing product experience

**Outcome:** A responsive interface clearly shows one repository entering three branches and one evidence-backed winner emerging.

**Files:**

- Create: `apps/web/src/routes/HomePage.tsx`
- Create: `apps/web/src/routes/RunPage.tsx`
- Create: `apps/web/src/components/RunForm.tsx`
- Create: `apps/web/src/components/BranchLane.tsx`
- Create: `apps/web/src/components/EvidenceTable.tsx`
- Create: `apps/web/src/components/PatchViewer.tsx`
- Create: `apps/web/src/components/CitationList.tsx`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/events.ts`
- Modify: `apps/web/src/App.tsx`
- Test: `apps/web/src/**/*.test.tsx`
- Test: `apps/web/e2e/happy-path.spec.ts`

- [ ] Design a focused two-screen flow: a home screen with repository/target inputs and a run screen with baseline, three branch lanes, evidence comparison, and winner patch.
- [ ] Make the default form point to the controlled fixture’s eventual public GitHub URL while still allowing another valid public URL.
- [ ] Consume SSE with reconnect support and render event timestamps, branch attempts, test counts, and terminal states without polling.
- [ ] Show exact Nebius, NVIDIA, Tavily, and Sandbox usage in a persistent “How this run works” panel.
- [ ] Keep the winner visual evidence-led: green status requires the verified test gate, while unsuccessful runs remain clearly labeled.
- [ ] Meet keyboard navigation, visible focus, semantic heading, color-contrast, reduced-motion, mobile-width, and empty/error/loading-state requirements.
- [ ] Add component tests for validation, live-event reduction, branch failure, winner display, and patch download.
- [ ] Run `pnpm --dir apps/web test && pnpm --dir apps/web lint && pnpm --dir apps/web build`; confirm all tests pass and Vite produces `apps/web/dist`.
- [ ] Run `pnpm --dir apps/web exec playwright test`; confirm the mocked happy path completes at desktop and mobile widths with no accessibility-critical failures.

### Task 11: Add end-to-end evaluation, safety tests, and cost evidence

**Outcome:** The project has repeatable evidence that the product works, fails safely, and uses credits predictably.

**Files:**

- Create: `evaluation/cases.yaml`
- Create: `evaluation/run_evaluation.py`
- Create: `evaluation/expected/pydantic-v1-app.json`
- Create: `services/api/tests/security/test_untrusted_repositories.py`
- Create: `docs/evidence/evaluation.md`
- Create: `docs/evidence/cost-and-latency.md`

- [ ] Define at least five fixture cases covering validators, settings/config changes, serialization methods, parsing methods, and mixed v1 compatibility imports.
- [ ] Record baseline behavior, expected migrated behavior, and minimum passing-test counts for each case.
- [ ] Add malicious fixture content that attempts prompt injection, secret discovery, network access, host path access, infinite output, and long-running processes; verify the sandbox boundary and orchestrator limits contain them.
- [ ] Run the complete real-integration evaluation at least three times and report pass rate, median duration, p95 duration, input/output tokens, Sandbox operations, and estimated credit usage.
- [ ] Capture failures honestly and convert repeated failure modes into specific regression tests.
- [ ] Run `.venv/bin/python evaluation/run_evaluation.py --cases evaluation/cases.yaml --output docs/evidence/evaluation.md`; confirm every case produces a terminal result and the report includes no credentials.
- [ ] Run `make check`; confirm unit, integration-mock, security, frontend, type, and build checks all pass before deployment.

### Task 12: Package and deploy one public Nebius-hosted demo

**Outcome:** A reproducible container serves the UI and API from a public Nebius Serverless Endpoint, with health monitoring and budget controls.

**Files:**

- Create: `Containerfile`
- Create: `.dockerignore`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/image.yml`
- Create: `deploy/nebius-endpoint.md`
- Create: `services/api/app/static.py`
- Modify: `services/api/app/main.py`

- [ ] Build the web assets in the first image stage and copy them into the FastAPI package in the final Python stage.
- [ ] Serve SPA fallback routes without intercepting `/api/*`; add cache headers for hashed assets and no-cache for `index.html`.
- [ ] Have CI run `make check`; have the image workflow build and push an immutable commit-SHA tag to GHCR.
- [ ] Add a non-secret deployment runbook using `IMAGE_REF`, `NEBIUS_SUBNET_ID`, and an authenticated local Nebius CLI profile.
- [ ] Deploy with a public endpoint and application-level quotas so judges need no credentials while arbitrary traffic cannot exhaust the budget.
- [ ] Verify with `curl -fsS "$BRANCHSHIFT_URL/api/health/integrations"`; confirm HTTP 200 and configured status for Nebius, Tavily, and Contree.
- [ ] Run the fixture through the public UI; confirm all three branches complete, the winner patch downloads, and the page remains functional after refresh.
- [ ] Document rollback as redeploying the previous immutable image tag; keep the last known-good tag in `deploy/nebius-endpoint.md` after every deployment.

### Task 13: Prepare the Devpost project and submission package

**Outcome:** A complete English submission demonstrates the product, exposes reproducible source code, and explicitly maps evidence to all four judging criteria.

**Files:**

- Create: `docs/submission/devpost-description.md`
- Create: `docs/submission/video-script.md`
- Create: `docs/submission/shot-list.md`
- Create: `docs/submission/judging-checklist.md`
- Create: `docs/submission/feedback.md`
- Modify: `README.md`

- [ ] Create a Devpost draft project named **BranchShift** after the end-to-end fixture works; select Coding & Agentic Engineering.
- [ ] Write the English description around a concrete problem, why parallel migration paths matter, how Nemotron/Token Factory/Tavily are used, and what evidence proves the winner.
- [ ] Add architecture, setup, safety model, demo URL, screenshots, exact model ID, Sandbox integration, and evaluation results to the public README.
- [ ] Record actionable Nebius feedback throughout development, including Sandbox API friction, documentation gaps, errors, latency, and suggested improvements.
- [ ] Script a video no longer than 2 minutes 45 seconds: problem (20s), architecture (25s), live three-branch run (75s), evidence/winner (30s), implementation and impact (15s).
- [ ] Record voice and screen without copyrighted music or third-party trademarks beyond permitted product references; upload the final video publicly to YouTube.
- [ ] Verify the public repository has the MIT license visible at the top level, no secrets in Git history, one-command setup, and a pinned release tag.
- [ ] Complete the Devpost fields but stop before final submission for user review.
- [ ] Submit by **29 October 2026 at 18:00 AEDT**, leaving more than 34 hours before the official deadline.

## Milestone schedule

| Dates (Sydney) | Milestone | Exit condition |
|---|---|---|
| 1–6 Sep | Foundation and technical spike | Three isolated Contree branches proven with real credentials |
| 7–13 Sep | First end-to-end migration | One strategy migrates the controlled fixture and passes tests |
| 14–20 Sep | Parallel agent core | Three strategies run concurrently and deterministic ranking selects a winner |
| 21–27 Sep | Product interface | Live branch lanes, evidence table, and patch download work against mocked and real runs |
| 28 Sep–4 Oct | Evaluation and safety | Five cases, prompt-injection fixture, timeouts, quotas, and redaction checks pass |
| 5–11 Oct | Public deployment | Nebius-hosted demo completes the controlled fixture from a fresh browser |
| 12–18 Oct | Reliability and polish | Three consecutive real runs pass; README and feedback draft are complete |
| 19–25 Oct | Submission production | Devpost draft, screenshots, video script, and final evaluation report are ready |
| 26–29 Oct | Freeze and submit | Release tag, public video, final link check, and Devpost submission completed |

## First seven days: concrete operating checklist

- [ ] Day 1: initialize the repository, scaffold packages, add the license, and make `make check` green.
- [ ] Day 2: obtain Token Factory, Contree, and Tavily credentials through their approved flows; run redacted provider health checks.
- [ ] Day 3: execute the Sandbox branching spike and record proof in `docs/evidence/sandbox-spike.md`.
- [ ] Day 4: create the Pydantic v1 fixture and make its baseline tests pass in a Sandbox.
- [ ] Day 5: retrieve official migration documentation through Tavily and obtain three schema-valid Nemotron strategies.
- [ ] Day 6: apply one generated unified diff in a branch and rerun the fixture tests.
- [ ] Day 7: demonstrate repository URL → baseline checkpoint → one tested patch locally, then decide whether the core integration is healthy enough to proceed.

## Risks and explicit controls

- **Sandbox Beta instability:** isolate all SDK calls behind `ContreeProvider`, record operation IDs, retry only idempotent reads, and preserve failed evidence. The two-day spike is the go/no-go gate.
- **Model-generated unsafe commands:** execute only inside the remote Sandbox; never mount host files or credentials; validate patches before applying; cap attempts, time, output, and resources.
- **Repository prompt injection:** treat repository contents as untrusted data, delimit them in prompts, never allow them to alter provider credentials or host instructions, and include adversarial fixtures.
- **Demo cost abuse:** public repositories only, size and duration limits, per-IP quotas, global concurrency limits, curated default fixture, and a daily credit ceiling.
- **LLM nondeterminism:** validate every structured response, allow one repair retry, use deterministic tests for winner selection, and keep replay fixtures for UI/tests.
- **Deployment without local Docker:** build images in GitHub Actions; make the local test path container-independent; use immutable image tags for rollback.
- **Solo-participant scope:** keep one migration target, one test framework, no GitHub OAuth, no PR creation, and no multi-user administration before submission.
- **Submission-day failure:** freeze feature work on 25 October, submit by 29 October, and keep the last working demo/image available through the judging period.

## Definition of done

- A judge can open the public URL without credentials, run the controlled fixture, and watch three Sandbox branches progress independently.
- The system demonstrably calls a configured NVIDIA Nemotron model through Nebius Token Factory at runtime.
- Tavily returns official migration sources that appear in the plan and final report.
- The winning branch is revalidated from the baseline checkpoint, has a downloadable unified diff, and is selected by deterministic evidence.
- The public repository contains an MIT license, English README, reproducible setup, architecture, safety notes, evaluation results, and no secrets.
- `make check` passes, the public smoke test passes, three consecutive real fixture runs complete, and the final Devpost links work in a logged-out browser.
- The demo video is public, English, and no longer than three minutes.

