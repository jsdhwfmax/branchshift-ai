# Deployment feasibility for BranchShift

Read-only audit, **10 September 2026**. No resource was created, deployed,
started, stopped or purchased. This audit does not prove that a working public
deployment exists.

## Conclusion

The original **Nebius AI Cloud Serverless Endpoint** direction is technically
credible for the FastAPI/React container. The official quickstart deploys
`nginx:alpine` on CPU resources, so the service is not restricted to hosting
model weights. Its name must not be confused with **Token Factory public
serverless inference**, which is the model API BranchShift calls.

Keep the existing Python orchestrator and genuine remote Sandbox pipeline.
Prepare one CPU container serving the UI and API together. Use a Nebius AI Cloud
Endpoint if its persistence and restart checks pass; use a regular CPU VM with
an independently retained block disk if the Endpoint cannot give the ledger a
verified durable filesystem. This is an architectural recommendation, not a
provisioning instruction or evidence of account eligibility.

Sites can host the frontend or an HTTP proxy, but the installed Sites deployment
contract cannot directly host this existing Python process and SQLite file.
Rewriting the orchestrator into Workers would add substantial scope and is
unnecessary to prove the actual migration product.

## What the official sources establish

| Service | Verified capability | Implication for BranchShift |
| --- | --- | --- |
| Token Factory inference | Hosted text, embedding and vision model APIs; public inference uses shared infrastructure. | Continue calling the NVIDIA model from the backend. No general FastAPI application-hosting contract is established by these inference pages. |
| AI Cloud Serverless Endpoint | Persistent container service with an HTTP interface; runs until stopped. | Suitable execution shape for a long-lived orchestration API. |
| AI Cloud Serverless Job | Finite background workload without the Endpoint's public request URL. | Not the website host. A future worker option, requiring explicit job dispatch/result persistence changes. |

Sources: [Token Factory inference](https://docs.tokenfactory.nebius.com/ai-models-inference/overview),
[public inference endpoints](https://docs.tokenfactory.nebius.com/public-serverless),
[Serverless AI overview](https://docs.nebius.com/serverless/overview).

The [official nginx quickstart](https://docs.nebius.com/serverless/quickstart/endpoints)
uses CPU platform `cpu-d3`, preset `4vcpu-16gb`, and a managed HTTPS URL. It
requires suitable project permissions and Compute/VPC quota. This is strong
evidence that an ordinary HTTP application can run; it does not prove
BranchShift's actual image, SSE stream or database behavior.

[Endpoint management](https://docs.nebius.com/serverless/endpoints/manage)
documents custom registry images, container commands, HTTP ports, environment
variables, secret injection, CPU-only resources, optional token authentication,
and bucket/filesystem mounts. An HTTP port has a managed HTTPS URL. Deleting
an Endpoint deletes its VM and boot disk. Its CLI documentation says an
additional public IP is unnecessary for managed HTTPS; verify the resolved URL
rather than blindly copying the quickstart's public-IP flag.

## Scale to zero and minimum running resources

Do not interpret “serverless” as free when no browser is connected. The current
[overview](https://docs.nebius.com/serverless/overview) describes an Endpoint
that listens until terminated. The [lifecycle](https://docs.nebius.com/serverless/lifecycle)
documents explicit stop/start transitions: `RUNNING` serves requests;
`STOPPED` can be started later. No request-triggered wake or idle automatic
shutdown contract was found in these current docs.

The inspected [Endpoint configuration](https://docs.nebius.com/serverless/endpoints/manage)
selects one platform/preset and storage. It does not expose a documented
`minReplicas`, `maxReplicas`, concurrency autoscaler or scale-to-zero setting.
This is a finding about the published contract, not proof that no account has
an additional preview feature. Do not base availability or price on an
unverified feature.

For the reviewable plan, keep **one CPU Endpoint continuously running** during
judge access. The smallest listed CPU preset depends on platform/region:
`cpu-e2/2vcpu-8gb` is listed in `eu-north1`; `cpu-d3/4vcpu-16gb` is the documented
CPU quickstart choice. These are VM resource sizes, not a service-level
minimum-replica setting. Validate selection in the actual project before
quoting a target. [CPU platforms](https://docs.nebius.com/compute/virtual-machines/types).

Manual shutdown during judging is incompatible with an always-available live
API unless a separately tested service can wake it and provide the required
access. That extra architecture is outside the minimal deployment. Persistent
mounts and backups have independent storage billing; stopping compute is not
evidence that all retained resources become free.

## Current application constraints

The inspected source has these concrete deployment dependencies:

- `services/api/app/storage/repositories.py` accepts only `sqlite:///` URLs,
  opens a local database and enables WAL. It is not an HTTP database client.
- `RunManager` launches long-running work with in-process `asyncio` tasks and
  a process-local semaphore. The run can outlive the request that creates it.
  A process restart loses those active tasks even if the database survives.
- The interface uses API requests plus SSE. The configured run timeout is
  900 seconds. The host must keep the process alive independently of the
  initial HTTP request; the public route must handle stream reconnects.
- The inspected FastAPI entrypoint serves API routes only and has localhost
  CORS settings. React static serving and a deployment image were not yet
  present in this audit's file inventory.
- Provider credentials belong only in backend runtime secrets. The browser
  must never receive the Nebius API key, project credential or Tavily key.

These observations identify necessary packaging work; they are not reasons to
replace the real backend with replay data.

**Preparation follow-through, later on 10 September:** same-origin static
serving was added by the parent task, and the
[container/deployment package](../../deploy/nebius-endpoint.md) is now present.
Its manual-only workflow and embedded scripts passed local syntax checks.
Docker is unavailable locally, so actual image build, cloud persistence and
hosted live execution remain unverified. The initial file-inventory observation
above records the earlier audit state, not a claim that packaging is still
absent.

## Persistence is the unresolved technical gate

Mounting a bucket is not sufficient evidence that a live SQLite database is
safe. Nebius documents durable network block disks separately from shared
filesystems, which are mounted as `virtiofs` and may attach to multiple VMs.
[Storage types](https://docs.nebius.com/compute/storage/types).
SQLite WAL requires cooperating processes on one host and is not supported
over a network filesystem; live backups must also account for committed WAL
content. [SQLite WAL documentation](https://www.sqlite.org/wal.html).

This does **not** establish that every single-host Nebius `virtiofs` use fails;
the mounted filesystem's exact SQLite semantics were not verified. Do not
assume compatibility, multi-replica safety or retention across Endpoint
replacement.

For the first public release:

1. Run one application process and one replica. Keep SQLite on a filesystem
   whose locking, sync and lifecycle behavior are verified. Use an absolute
   database path outside image source files.
2. Exercise concurrent event writes and reads, terminate/restart the process,
   and check database integrity plus retained run/patch history. Test platform
   stop/start and release replacement separately; they are different events.
3. Use SQLite's backup facility for consistent backups. Keep them outside the
   resource that a deployment replacement deletes; prove restoration once.
4. On startup, reconcile orphaned nonterminal runs with a clear interrupted
   status and retained partial evidence. Do not leave them spinning forever
   or automatically repeat uncertain cloud writes.
5. If Endpoint storage cannot satisfy these checks without an added database
   service, retain the same container on a regular CPU VM, binding a persistent
   network block disk into its data directory. Add HTTPS ingress for that
   route. The application and Sandbox integration remain the same.

Longer-term replicas would require durable job coordination and shared storage
designed for multiple workers. Neither is a prerequisite for a small,
single-instance competition demo.

## Sites comparison

The installed Sites **0.1.57** building and hosting skills, plus their hosted
runtime and persistence references, were read locally as research sources.
They are plugin documentation, not files distributed with this repository.
This comparison records that inspected deployment contract.

| Sites option | Supported contract | Fit |
| --- | --- | --- |
| Static React build | Static `index.html` output; static builds have no runtime bindings/secrets | Can display the UI, but still needs a public Python backend and its availability budget |
| Worker-backed frontend/proxy | Cloudflare-compatible ESM `fetch(request, env, ctx)` entrypoint; 128 MB isolate memory; HTTP-based integrations | Can proxy API/SSE to the real Python host after testing; adds a network/access layer |
| Full backend replacement | D1 for records, R2 for blobs; no raw TCP; deployment expects Worker ESM | Not a drop-in deployment of FastAPI, the Contree Python SDK, local SQLite or in-process Python jobs |

A Sites-only replay would not meet the intended live migration outcome. A split
frontend/backend is legitimate but adds CORS or proxy configuration, SSE
validation and a second deployment. Prefer one origin for this release unless
existing approved hosting makes the split meaningfully simpler.

Sites registration defaults to private access. Any eventual judge-facing Site
must have its actual public/evaluator access verified. This audit created no
Site and changed no hosting manifest.

## Official credit offers and what remains unknown

| Official offer | Verified scope | Hosting implication |
| --- | --- | --- |
| Hackathon online promo | $25 **Token Factory** credit; activation code `NEBIUS-DEVPOST-GLOBAL26` | No stated AI Cloud/Serverless coverage |
| Nebius Builders Program | Another $25 Token Factory credit; additional program benefits | No stated general Cloud hosting grant |
| Builders & Brews: Hack Edition | Attendees can unlock additional AI Cloud, Token Factory and Tavily credits | Cloud amount, expiration, redemption conditions and this user's eligibility remain unknown |

These offers are listed on the [official hackathon resources page](https://nebiusglobalaihackathon.devpost.com/resources).
Its [online promo form](https://nebius.com/promo-code?utm_promo_activation_code=NEBIUS-DEVPOST-GLOBAL26&utm_promo_code_type=Token_Factory&utm_promo_event_code=2026-devpost-global-ai-hack)
explicitly selects `Token_Factory` in the linked offer parameters. The
[Builders Program](https://dev.nebius.com/builders) and
[Builders & Brews event hub](https://nebius.com/events/builders-and-brews) are
the linked program/event paths. This audit did not submit a form or redeem a
code. A separate, generally available AI Cloud promo application for this
hackathon was **not verified**.

The [Serverless AI Builders Challenge](https://nebius.com/serverless-ai-builders-challenge)
is a different competition whose page already shows results. Its advertised
Nebius-credit prizes do not establish a hosting grant for this entry.

For any Cloud grant already received, read its actual email or account credit
entry for covered services, amount, remaining balance, expiry and payment
conditions before including it in the budget. The email screenshot titled
“Here is your promo code from Nebius” previews **Token Factory** credit, so the
title alone is insufficient evidence of AI Cloud credit.

## Illustrative hosting cost

Serverless AI uses **Compute VM pricing and quotas**; mounted buckets and
filesystems have separate charges.
[Serverless pricing](https://docs.nebius.com/serverless/pricing-quotas).
The Builder Program calls its grant **Token Factory credit**, and Token Factory
billing describes promo codes as Token Factory credits.
[Builder Program](https://dev.nebius.com/builders),
[Token Factory billing](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new).

**No inspected source states that this user's existing $25 Token Factory grant
pays for AI Cloud Compute or Serverless Endpoint hosting.** Current remaining
balance, expiration, Sandbox charging and any separate AI Cloud promotion are
unknown. Do not count that grant as a hosting budget or assume it is a hard
limit on charges.

Published CPU rates are $0.012 per vCPU-hour plus $0.0032 per GiB-hour; ordinary
network SSD storage is $0.071 per GiB per 730 hours. Taxes and other services
are additional. [Compute prices](https://docs.nebius.com/compute/resources/pricing).

From the internal submission target (29 October, 18:00 AEDT) through judging
end (16 December, 07:00 AEDT) there are **1,141 hours**. For a simple retention
buffer through the whole of 16 December, keep it available until **17 December,
00:00 AEDT**: **1,158 hours**. Arithmetic examples:

| Resources | Compute per hour | Through official judging end | Through 16 December |
| --- | --- | --- | --- |
| 2 vCPU / 8 GiB | $0.0496 | $56.59 | $57.44 |
| 4 vCPU / 16 GiB | $0.0992 | $113.19 | $114.87 |

These are estimates from published unit rates, not quotes or selected
resources. A 32 GiB ordinary network disk adds approximately $3.55 over that
official interval, or $3.60 through 16 December; registry, backup/storage,
network, model, Tavily, Sandbox and tax costs are excluded. **Earlier deployment
increases the total**: calculate from the actual provisioning timestamp, not
the submission target. These figures are USD before tax and do not assume any
credit discount or scale-to-zero savings.

The [platform list](https://docs.nebius.com/compute/virtual-machines/types)
documents `cpu-e2/2vcpu-8gb` in `eu-north1` and `cpu-d3/4vcpu-16gb` more broadly.
Actual project availability and suitable capacity must be checked. Avoid a GPU
host for the orchestration service: its inference and code execution already
happen in the remote providers. Avoid accidentally retaining the example's
250 GiB disk or large shared-memory default without a need.

## Recommended public-demo architecture

```text
Browser
  -> one HTTPS origin
     -> built React assets
     -> FastAPI API and SSE (one process)
        -> durable SQLite ledger + consistent external backups
        -> Nebius Token Factory NVIDIA inference
        -> Tavily official-document retrieval
        -> Token Factory Sandbox baseline and three real child strategies
```

Keep the service reachable throughout the judging-access period documented in
[competition requirements](competition-requirements.md). Serve retained real
results without new inference cost; clearly label replay when offered. New live
runs must still be possible for evaluators. Provide a reserved evaluator access
route and budget alongside bounded public admission, concurrency, retries,
repository scope, wall time and outputs. A global daily cutoff alone could
prevent required evaluation; controls must distinguish public abuse from the
actual judging path without exposing provider keys.

Measure the full live run's token usage and operations before deciding that
remaining provider credits can cover judging. Keep the source/video/recorded
results available, but do not treat them as replacements for required working
project access. Keep an immutable release and a tested rollback route.

## Login, decisions and remaining checks

| Needed next | Evidence or user involvement |
| --- | --- |
| AI Cloud account access | User login at `console.nebius.com` if no reusable session exists; confirm tenant/project and editor permission. Token Factory key alone is not evidence of Cloud management access. |
| Cloud resource eligibility | Inspect region, subnet, CPU/storage quota and billing account read-only; do not invent IDs or a payment method. |
| Hosting budget | Prepare the actual tenant/project, region/preset, disk, image/registry, secret names, public-access mode and cost from provisioning through 16 December. Then confirm applicable Cloud credits or an authorized total budget if needed. No spend authorized by this audit. |
| Tooling | `nebius` and `docker` were absent from this shell's PATH; `~/.nebius/config.yaml` was absent. `gh` was present. Existing browser login was not inspected. An authenticated console route or CLI setup and an image-build route are needed. |
| Container image | Build the actual UI/API image, install the Contree optional dependency, use an immutable image reference, and verify registry pull access. No image workflow was claimed ready here. |
| Runtime secrets | Set actual provider values through the chosen host's secret mechanism; verify no keys are embedded in the image or frontend. |
| Storage/restart gate | Complete the persistence checks above before a judge-facing release. |
| Public behavior | Verify health, real migration, SSE reconnect, refresh, failure state, patch download and evaluator access through the exact HTTPS URL. |

The safe independent next action is container/static-serving preparation and
restart handling, while obtaining account and budget facts read-only. Any
budget request should be the final approval of a concrete, reviewable target,
not a premature open-ended hosting question. Deployment is not blocked by a
model-only Endpoint restriction; it is pending packaging, persistence
evidence, AI Cloud access and an appropriate hosting budget.
