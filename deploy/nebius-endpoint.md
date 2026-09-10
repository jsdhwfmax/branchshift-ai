# BranchShift container deployment runbook

Updated 10 September 2026. The Linux `amd64` image at
[commit `99fae2fab173d6a34e085a2f5939bff35c70d33c`](https://github.com/jsdhwfmax/branchshift-ai/commit/99fae2fab173d6a34e085a2f5939bff35c70d33c)
was built and smoke-tested successfully in
[image workflow `34440192693`](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34440192693).
The dispatch used `publish=false`; **GHCR publication was skipped**. No public
image digest, AI Cloud storage result or hosted live deployment is established
by this run.

[CI `34440006894`](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34440006894)
passed at the same commit: Ruff, mypy across 34 source files, frontend type
checks, 202 API tests, 13 baseline fixture tests, 27 frontend tests and the
production UI build. The image workflow separately passed runtime SDK imports,
UID `10001`, same-origin UI and route refresh, a completed mock run, patch/report
retrieval, and retention of that completed run and patch after replacing the
container against the same runner-local bind directory. These are **mock and
local-bind persistence checks**, not Cloud persistence or hosted live evidence.

Local preparation checks passed: YAML parsing and the manual-only trigger,
all four embedded Bash scripts with `bash -n`, embedded Python syntax,
referenced source-file existence, runtime database/user/worker declarations,
and local documentation links. The local tool versions are Python 3.13.9,
Node 24.14.0 and pnpm 11.19.0. Neither Docker nor `actionlint` is installed in
this shell; the actual container build/runtime evidence above comes from the
GitHub-hosted Linux runner. Existing source tests and image smoke checks remain
separate from validation of a Cloud deployment.

## Deployment target

Run one Linux `amd64` CPU container containing the Vite React build and Python
3.13 FastAPI API. Uvicorn listens on port **8000** with **one worker**, as UID/GID
**10001:10001**. Keep one instance: the SQLite ledger and background job manager
are not a distributed worker system.

The production database URL is **`sqlite:////data/runs.db`**, which resolves to
the absolute path `/data/runs.db`. The plain string `/data/runs.db` is not a
valid URL for the current repository adapter. The `/data` directory in the
image is only a mount target. It provides **no retention guarantee** itself.

The preferred host is a Nebius AI Cloud CPU Serverless Endpoint, subject to
the storage and restart gate below. This service supports ordinary HTTP
containers; it is distinct from Token Factory model inference. If Endpoint
storage cannot preserve the ledger across the relevant lifecycle operations,
use the same container on a regular CPU VM with an independently retained
network block disk and HTTPS ingress. Do not replace live providers with mock
mode to fit a different host. [Feasibility and official sources](../docs/evidence/deployment-feasibility.md).

## What is prepared

- [Containerfile](../Containerfile): Node 24 and pnpm 11.19.0 compile the UI;
  the final Python image installs `services/api[contree]` and serves the UI/API
  on the same origin. The source layout is retained so `app.main` resolves
  `apps/web/dist` correctly. Runtime does not require Node or a local Docker
  daemon; generated code runs through remote Token Factory Sandboxes.
- [.dockerignore](../.dockerignore): the context allows required source and
  package files only, excluding `.env` files, local databases, keys, caches,
  installed dependencies and generated output.
- [Manual image workflow](../.github/workflows/image.yml): `workflow_dispatch`
  only. Default `publish=false` builds and checks a Linux CPU image without
  logging in or pushing. The optional publish step follows successful checks,
  authenticates with `GITHUB_TOKEN`, and targets
  `ghcr.io/jsdhwfmax/branchshift-ai:<full-commit-sha>` only. It refuses an
  existing SHA tag and fails closed on an uncertain registry lookup.

The workflow creates no Nebius resources, changes no package visibility and
has no push, pull-request or release trigger. It has been published and
dispatched with `publish=false`; registry publication remains a separate
action. An authorized publish dispatch writes a GHCR package and consumes
applicable Actions/package usage. [GitHub manual triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow),
[GHCR publication](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images).

After publication, record and deploy the **image digest**
`ghcr.io/jsdhwfmax/branchshift-ai@sha256:…` printed in the workflow summary.
A full SHA identifies source; the digest identifies built bytes. Base-image
tags and Python dependency ranges can change between builds, so rebuilding the
same commit is not a byte-for-byte reproducibility guarantee. Never overwrite
an accepted release tag or substitute a `latest` tag in the deployment record.

## Build and check locally when Docker is available

From the repository root, build a local image without publishing:

```sh
docker build --platform linux/amd64 --file Containerfile --tag branchshift:local .
```

Use a fresh disposable **local test** directory, writable by UID/GID 10001.
On a Linux Docker host, prepare it with owner `10001:10001` before binding it.
The following starts offline mock mode; it sends no provider calls:

```sh
docker run --name branchshift-local --detach \
  --publish 127.0.0.1:8000:8000 \
  --mount type=bind,src=/absolute/test-data,dst=/data \
  --env BRANCHSHIFT_MODE=mock \
  branchshift:local
```

Open `http://127.0.0.1:8000`, create a sample run and retain its URL. Check the
patch/report downloads, then stop and remove only the test container. Start a
replacement with the same bind directory and confirm that completed run and
patch remain. A passing local bind-mount check does not prove Endpoint
persistence or live provider success.

The manual workflow automates checks for SDK imports, the nonroot user, UI/API
serving, a completed mock run, patch/report retrieval, SPA refresh and retained
records after container replacement against a runner-local bind directory.
These checks **passed** in the verified
[image smoke step](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34440192693/job/102753435169#step:5:1),
whose logs record a replacement container retrieving the retained completed
run and the final successful bind-retention assertion. This does not verify a
Nebius mount, Cloud lifecycle operation or live provider call. The image health
check requests `/api`; it is process liveness, not proof of working credentials
or remote providers.

## Complete this deployment record before provisioning

| Field | Selected value or evidence needed |
| --- | --- |
| Cloud tenant / project | Exact existing IDs, account access and role; not yet inspected |
| Region / subnet | Exact project-supported region and subnet; not yet selected |
| Endpoint platform / preset | Prefer CPU only; compare `cpu-e2/2vcpu-8gb` if available with the documented `cpu-d3/4vcpu-16gb` |
| Image | Linux image built and smoke-tested at `99fae2f`; GHCR publish skipped, published immutable digest pending |
| Registry access | Prove the chosen host can pull; private GHCR requires a supported credential path, or separately approved package visibility |
| HTTP interface | Container port 8000, managed HTTPS URL; actual URL pending |
| Runtime identity | Container UID/GID 10001:10001; minimum host IAM needed |
| Data mount | Exact durable resource, `/data`, ownership, size, retention and restart/replacement evidence; pending |
| Backup target | Independently retained destination plus tested SQLite backup/restore; pending |
| Instance policy | One running instance, one worker; no unverified automatic scale-to-zero |
| Access policy | Public demo/evaluator path tested without exposing provider credentials; pending |
| Availability | From actual deployment through **16 December 2026**, with buffer until **17 December 00:00 AEDT** |
| Credits / budget | Applicable AI Cloud credit amount/expiry and approved maximum cost, including runtime providers; pending |

The exact endpoint configuration and account estimate must be shown before any
needed spending approval. Prepare the build and storage checks first; do not
ask an open-ended budget question while the target is still unspecified.

## Runtime configuration

Set these in the chosen host's runtime configuration, never in frontend build
arguments, repository files or image layers:

| Variable | Value / handling |
| --- | --- |
| `BRANCHSHIFT_MODE` | `live` for the genuine public demo; image defaults to `mock` for offline checking |
| `DATABASE_URL` | `sqlite:////data/runs.db` on the verified mount |
| `MAX_CONCURRENT_RUNS` | `1` initially; add admission limits because concurrency alone does not cap total spending |
| `RUN_TIMEOUT_SECONDS` | `900` initially; enforce provider and output budgets as well |
| `NEBIUS_API_KEY` | Runtime secret; authorized Token Factory credential |
| `NEBIUS_PROJECT_ID` | Correct Token Factory project ID; runtime configuration |
| `TAVILY_API_KEY` | Runtime secret |
| `NEBIUS_BASE_URL` | `https://api.tokenfactory.nebius.com/v1/` unless the verified account route differs |
| `NEMOTRON_MODEL` | `nvidia/Nemotron-3-Ultra-550b-a55b`, as recorded in the retained live evidence |
| `NEMOTRON_ENABLE_THINKING` | `true`, matching the successful live configuration |
| `CONTREE_API_URL` | `https://api.tokenfactory.nebius.com/sandboxes` unless verified otherwise |
| `CONTREE_IMAGE` | The actual usable Sandbox image identifier from the successful account-level integration test |

The application accepts the live provider values directly as environment
variables. Use Nebius's documented secret-injection mechanism rather than
passing credentials in a shell command. Do not copy the development `.env`
into the image. [Endpoint configuration and secrets](https://docs.nebius.com/serverless/endpoints/manage).

The container exposes one origin, so no production `VITE_API_BASE` is required.
Keep any ingress authentication compatible with browser API requests and SSE;
requiring a raw Cloud IAM bearer token for every visitor is not a complete
judge-facing login experience. Do not share a provider or management credential
as the evaluator password.

## Storage and availability release gate

1. Select durable storage whose locking and sync semantics work with SQLite
   WAL. Do not place the live database on an object bucket merely because it
   can be mounted. A shared filesystem needs explicit compatibility evidence.
2. Verify UID/GID access, concurrent reads/writes, SQLite integrity and retained
   run/patch history after process restart, Endpoint stop/start and deployment
   replacement separately. Deleting an Endpoint deletes its boot disk; keep
   recoverable records outside that deletion boundary.
3. Take a consistent SQLite backup through its backup facility and restore it
   into a separate test location. Copying only `runs.db` while WAL writes are
   active is not a consistent backup procedure.
4. Verify startup reconciliation of interrupted nonterminal runs. Retained
   SQLite rows do not restore in-process `asyncio` jobs. An interrupted run
   must remain understandable, not hang indefinitely or silently replay writes.
5. If these checks cannot be satisfied on an Endpoint, use a CPU VM with a
   separately retained network block disk, bind `/data` to that disk and
   configure HTTPS. Re-run the same public behavior checks on that exact host.

Serverless Endpoints currently document manual stop/start, not idle request
autoscaling or a `minReplicas=0` guarantee. Budget a continuously running CPU
instance. Mounted storage and backups can have independent charges. Details
and the current source limitations are in the [feasibility audit](../docs/evidence/deployment-feasibility.md).

## Budget and judge-access gate

The known $25 offer is **Token Factory** credit, with no verified coverage for
AI Cloud hosting. The hackathon mentions extra Cloud credits for in-person
Builders & Brews attendees without a stated amount or general online Cloud
grant. Confirm any actual Cloud grant and its expiry from the account or email.

At published unit prices, one 2 vCPU / 8 GiB instance is about **$0.0496/hour**;
4 vCPU / 16 GiB is **$0.0992/hour**, before storage and taxes. From 29 October
18:00 AEDT through all of 16 December, compute is about **$57.44** or **$114.87**,
plus about **$3.60** for a 32 GiB ordinary network disk. These are illustrative
USD amounts, not an approved configuration or total bill. Hosting earlier
increases the duration. Inference, Sandbox, Tavily, registry, backups, network
and taxes need their own allowance. [Published pricing and arithmetic](../docs/evidence/deployment-feasibility.md).

Before public live admission, cap queued work, allowed repository scope,
retries, output and provider use; reserve sufficient evaluator capacity.
Serving retained real results is cheap, but judges must retain access to the
working project. An exhausted public quota must not lock evaluators out. Keep
the service reachable through the stated access window and make the final
cleanup date an explicit later action, not an unapproved automatic shutdown.

## Public acceptance evidence to record

- Exact image digest, Git commit, host configuration, deployment timestamp and
  HTTPS URL; accessible from a fresh browser session.
- UI load and route refresh; `/api/health/integrations` reports `live` and
  configured values without exposing secrets.
- A complete live run on the hosted Python pipeline, real Sandbox checkpoint
  identities, verified winner, patch/report downloads and model usage record.
- SSE connection, reconnect and retained history through the public ingress;
  a clear real failure state when a provider request fails.
- Database restart/replacement/backup evidence, interrupted-run behavior,
  budget controls and the reserved evaluator access path.

Until those facts exist, keep public deployment, live hosted execution and
judge availability marked **pending** in submission materials.
