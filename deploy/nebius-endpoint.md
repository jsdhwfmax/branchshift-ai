# BranchShift container deployment runbook

Updated 10 September 2026. The Linux `amd64` image at
[commit `63cf7fdb4c62e119facb87fe108e9c278960a5c1`](https://github.com/jsdhwfmax/branchshift-ai/commit/63cf7fdb4c62e119facb87fe108e9c278960a5c1)
was built, smoke-tested and published successfully in
[image workflow `34446125409`](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34446125409).
The dispatch used `publish=true`; the publish step completed successfully.

```text
ghcr.io/jsdhwfmax/branchshift-ai:63cf7fdb4c62e119facb87fe108e9c278960a5c1
ghcr.io/jsdhwfmax/branchshift-ai@sha256:e1c84566cbe08d4ae5548288dea59cab78ea00dc8f596d4d34ca98c74f3ba9ac
```

The [current release evidence](../docs/evidence/runtime-release-63cf7fd/README.md)
separates source publication, CI, image publication and the local live check.
Anonymous registry reads returned the 2,204-byte manifest with a matching
digest and a matching configuration blob declaring Linux `amd64`, user
`10001:10001` and the exact source revision. No image layers were downloaded.
The eventual host still needs to pull the exact digest. No AI Cloud resource,
Cloud filesystem retention or hosted live deployment is established here.

[CI `34445971465`](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34445971465)
passed all 16 steps at the same commit: Ruff, mypy across 40 files, frontend
type checks, 324 API tests, 13 original fixture tests, 29 frontend tests,
the production UI build, Chromium installation and four desktop/mobile
Playwright checks using controlled fixtures. The image workflow's eight steps
passed, including runtime SDK
imports, UID `10001`, same-origin UI and route refresh, a completed mock run,
patch/report retrieval, and retention after replacing the container against
the same runner-local bind directory. These are mock/local-bind checks;
Cloud storage and live provider execution inside this image remain unverified.

Separately, the local production UI created live run `3ddea183879b` with source
and baseline `63cf7fd`. Two candidates passed; minimal won with 44 changed lines
and passed all 13 tests again from a distinct clean checkpoint. Desktop/mobile
refresh and actual browser JSON/patch downloads matched the stored evidence;
Markdown and JSON exports repeated byte-for-byte. This is a local live check,
not a provider run in the published image or a public Cloud deployment.

The historical `92c733a` image and 15-slot live cohort retain their original
receipts. The newer immutable image above adds the interface, Markdown report
and repository-size gate without rewriting that cohort's provenance.
Docker remains unavailable in the local shell; actual Linux build evidence
comes from the GitHub-hosted runner. Do not reuse this image's test receipt for
later source commits without building and checking their actual images.

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
has no push, pull-request or release trigger. It was dispatched with `publish=true` for the verified image above. An authorized publish dispatch writes a GHCR package and consumes
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
[image smoke step](https://github.com/jsdhwfmax/branchshift-ai/actions/runs/34446125409/job/102771195497#step:5:1),
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
| Image | Published and smoke-tested at `63cf7fd`; use the exact digest above after host pull verification |
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
| `MAX_CONCURRENT_RUNS` | `1` initially; executing slots, combined with the persistent HTTP admission controls below |
| `RUN_TIMEOUT_SECONDS` | `900` initially; enforce provider and output budgets as well |
| `MAX_REPOSITORY_BYTES` | `52428800` (50 MiB); reject a larger tracked checkout before installing dependencies; excludes transient clone, `.git` and installed-package size |
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

### Public run admission configuration

`POST /api/runs` checks actual request bytes before parsing JSON or admitting a
run. This includes requests without `Content-Length`, false length headers and
chunked bodies. An oversized body receives **413**. Validated creates then use
one SQLite `BEGIN IMMEDIATE` transaction to check all limits and insert the
admission record plus run. An exceeded limit receives **429** with an explanation
and, for daily or occupied-slot limits, `Retry-After`. Rejection creates no run
and starts no provider work. Unavailable admission storage fails closed with
**503**. Invalid request data does not consume quota.

| Variable | Application default | Meaning |
| --- | --- | --- |
| `HTTP_MAX_BODY_BYTES` | `8192` | Actual bytes permitted for a create request; must be positive |
| `HTTP_DAILY_RUN_LIMIT` | `5` | Global accepted HTTP attempts per UTC calendar day |
| `HTTP_LIFETIME_RUN_LIMIT` | `20` | Global accepted HTTP attempts since admission tracking was installed on this database |
| `HTTP_MAX_PENDING_RUNS` | `2` | Waiting slots beyond `MAX_CONCURRENT_RUNS`; zero permits no extra queue |
| `HTTP_CLIENT_DAILY_RUN_LIMIT` | `2` | Accepted attempts per client per UTC calendar day |
| `HTTP_CLIENT_MAX_OUTSTANDING_RUNS` | `1` | Maximum unfinished HTTP runs for one client |
| `FORWARDED_ALLOW_IPS` | Explicitly set to an empty string | Disable Uvicorn's forwarded-client rewriting unless a sanitizing proxy and its exact trust boundary have been verified |

These are conservative application defaults, **not an approved deployment
budget**. Record actual chosen values with the deployment estimate. Run counts
bound attempts, not dollar cost; provider/output/timeout budgets remain separate.
Zero daily, lifetime or client allowances close admission without affecting
`GET` run summaries, SSE history, reports, patches or health. Keep judge evidence
reachable when public capacity is exhausted; any additional evaluator capacity
requires an operator budget decision, not a secret browser bypass.

The SQLite ledger counts failed and cancelled attempts, including runs stopped
during a restart. Completion frees outstanding slots but never refunds daily or
lifetime allowance. Daily accounting rolls at **00:00 UTC**, using the server
clock. History and the client HMAC salt live beside run evidence in the same
database and must survive restart, deployment replacement and backup/restore.
Do not delete or rotate that database to refresh quota. Existing runs from before
this feature are not retroactively charged, but every nonterminal run occupies
capacity. The slot check reserves active capacity immediately, before a newly
accepted background task starts; total unfinished work cannot exceed executing
slots plus pending slots through this HTTP entry point.

The application ignores `Forwarded` and `X-Forwarded-For` request headers. It
keys client limits from the ASGI client address using a persisted random HMAC
salt; no raw IP or client key appears in public run evidence. Set
`FORWARDED_ALLOW_IPS=""` in the **host/process environment before Uvicorn starts**;
loading it only from application `.env` may happen after server configuration.
ASGI already reflects any server-level proxy rewriting, so trusting arbitrary
forwarded headers upstream defeats peer-based limits. With rewriting disabled,
visitors behind an ingress proxy or shared NAT may share a client quota. This is
a bounded spending control, not a unique-person identity mechanism. IPv4-mapped
IPv6 addresses are normalized to the equivalent IPv4 client.

SQLite transactions serialize admission across connections and keep checks plus
run insertion atomic through interruption. Continue to deploy **one instance and
one worker**: the execution semaphore and startup recovery are process-local,
and multiple workers against this database are not supported. Startup cancels
interrupted runs before serving requests; this releases their slots while
retaining charged history. Graceful shutdown does the same. A remote operation
already submitted before a crash may outlive the local process; admission
accounting does not establish provider-side cancellation or exact spending.

Direct operator/CLI calls to `RunManager.create` deliberately bypass **HTTP**
admission. There is no HTTP parameter, mode switch or forwarded-header bypass.
Use a separate experiment database/process for CLI evaluations while the public
service runs, and budget those provider calls separately. CLI runs sharing the
database are included in HTTP outstanding-slot checks, but concurrent CLI
processes are not controlled by the public worker's execution semaphore.

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
