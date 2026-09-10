# UI browser evidence

The frozen UI snapshot was checked on **10 September 2026** using production
assets served by a local HTTP mock. **Four Chromium browser tests** passed
across desktop and mobile projects, and **29 component tests** passed in four
files. Frontend lint and the production build also passed. These checks made
no live provider calls and do not establish hosted behavior, Cloud persistence
or a new real migration.

The [derived validation receipt](ui-browser-validation.json) retains commands,
results, screenshot hashes and the frozen UI patch digest. Its source receipt
SHA256 is
`f8f032d7478494102eb0901cd3e6194d0928315ee2fc290d48a9347e08d9cff7`.
Private absolute paths were replaced with repository-relative paths. The
checks describe the isolated snapshot; later integration checks are separate.

## What was exercised

- Native EventSource reconnect with `Last-Event-ID=2`, replay deduplication and
  terminal-state refresh.
- Actual browser downloads of the expected patch and JSON bytes.
- Keyboard skip link, invalid-field focus, route-heading focus and evidence
  table scrolling; reduced-motion behavior; no page-wide horizontal overflow
  at mobile widths of 393px and 320px.
- Unavailable service, failed run and missing-run states.
- Axe WCAG 2 A/AA and 2.1 AA checks returned zero violations on the tested
  home, validation-error, completed, failed and missing-run pages.

Automated checks do not prove full accessibility conformance or screen-reader
support. The lead reviewer checked desktop composition and the service/sample
disclosures. This was not an exhaustive mobile legibility review: downscaled
full-height screenshots limit that assessment.

## Retained screenshots

These PNGs are copied byte-for-byte from the validation run. Pixel dimensions
can differ from CSS viewport dimensions because of device scaling and
full-page capture.

| View | Retained image |
| --- | --- |
| Desktop preflight | [Original PNG](../images/ui-preflight-desktop.png) |
| Desktop completed sample | [Original PNG](../images/ui-completed-desktop.png) |
| Mobile completed sample | [Original PNG](../images/ui-completed-mobile.png) |

The completed view is explicitly labeled **SAMPLE REPLAY** and says:

> Metrics, events, and the patch illustrate the workflow using a fixed sample. No providers were called and no repository migration was verified in this run.

This label also applies to the sample metrics, events and patch visible in the
screenshots. See the [browser test](../../apps/web/e2e/happy-path.spec.ts) and
[Playwright configuration](../../apps/web/playwright.config.ts) for the
exercised states and browser projects.
