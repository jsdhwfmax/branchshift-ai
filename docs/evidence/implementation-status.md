# Implementation choices and remaining delivery work

Updated 10 September 2026. This reconciles the original
[implementation plan](../superpowers/plans/2026-08-31-branchshift-implementation.md)
with the working product. A changed library or file layout is distinguished
from an unverified product outcome. The original plan remains available.

## Deliberate implementation choices

| Original method | Current implementation and reason |
| --- | --- |
| SQLAlchemy/aiosqlite persistence | SQLite's standard-library adapter, a process-local async lock and explicit transactions. The single-worker deployment keeps one owner for jobs; stored runs/events survive refresh and container replacement. The new admission transaction is atomic across connections. No distributed-worker claim is made. |
| OpenAI Python client | Direct `httpx` calls to Token Factory's compatible chat-completions endpoint, with validated structured responses and exact runtime model identity. Live usage is retained. |
| Python 3.9 starting target | API requires Python 3.10 or newer; the verified complete runtime and published image use Python 3.13 with the pinned Contree prerelease. |
| Model-generated unified diffs | Nemotron supplies bounded complete-source replacements for exact declared files. The application constructs and validates the unified diff, avoiding malformed model-written hunk headers. Manifests are migrated deterministically and tests remain protected. |
| Model-written ranking explanation | Candidate ranking and its numeric explanation come directly from stored metrics. This intentionally avoids adding unverified model-generated numbers to the result. Nemotron still produces grounded strategies and source edits; it cannot select the winner. |
| YAML evaluation input | Versioned JSON case and attempt manifests with equivalent case contracts, plus a predeclared round/case matrix. Historical development attempts remain a separate cohort. |
| Archive-size rejection | A configured whole-repository tracked-checkout byte gate runs after clone and before dependency installation. This is a pre-install acceptance gate, not a clone-transfer or total Sandbox disk limit; see [its exact scope](repository-size-gate.md). |
| Explicit Sandbox CPU/memory/network controls | The installed SDK exposes runtime and collected-output limits, but this adapter does not expose per-call CPU/memory/egress controls. Selected canaries and provider-reported timeouts were tested; egress is allowed. Missing guarantees are disclosed in [security evidence](security-boundaries.md). |

## Evidence boundaries

The Git-history scan at `173d431` examined 240 locally reachable blobs for the
two currently configured credential values and private-key markers, with no
matches. The next 39 published files were checked for those credential values
before commit, and anonymous HTTP reads matched their committed bytes. The
[retained receipts](runtime-release-92c733a/runtime-publication-92c733a.json)
identify the exact published files. This is a scoped secret check, not proof
that every possible historical secret format is absent.

Repository evidence and patches have byte bounds; setup and remote execution
have timeouts. The pre-install gate rejects a checkout whose tracked regular
files plus symbolic-link lengths exceed `MAX_REPOSITORY_BYTES` (50 MiB by
default). It checks the whole repository even when a project subdirectory is
selected. Clone downloads, transient storage, `.git`, later dependency growth
and CPU/memory/egress limits remain outside this gate. The original archive-size
requirement therefore has a narrower, explicitly named implementation; see
[repository size scope and tests](repository-size-gate.md). The historical
`92c733a` matrix predates this gate and is not evidence that it ran there.
The intended first release is a bounded public demo with a small controlled
fixture, persistent creation quotas and retained evidence; the security document
states the limits for other untrusted repositories.

## Work still being verified

- Three complete rounds of the five live cases finished with 15/15 qualified
  migrations at frozen commit `92c733a1338cc7abdbcf04ca00be363158fd126c`;
  [the complete cohort](../../evaluation/series-20260910/README.md) preserves
  all slots, candidate failures, usage, estimates and original exports.
- The UI now uses event-driven updates, persistent service explanation and
  recorded proposal-attempt progress. [Browser evidence](ui-browser.md) covers
  desktop/mobile mocked flows, reconnect/download/refresh, keyboard and selected
  accessibility checks. The combined code passed 324 API tests, 13 original
  fixture tests, 29 component tests, Ruff, mypy and production build checks.
  Those later changes do not alter the frozen matrix. A new real release
  verification is pending.
- The exact `92c733a` image was built, smoke-tested and published, and its
  manifest was read anonymously. A later source change needs its own build.
- Nebius Cloud account access, concrete hosting/storage/budget selection,
  actual public live run, refresh/download and judge availability remain pending.
- The 130-second local recorded-evidence video exists. Its final hosted version,
  public YouTube playback, final release tag, Devpost project creation and final
  accepted submission remain pending. The complete competition entry is not done.

The single-strategy comparison is a possible later experiment, not an added
mandatory gate. Unknown Sandbox billing units or the lack of a final invoice
do not invalidate explicitly scoped token estimates and observed SDK counts.
