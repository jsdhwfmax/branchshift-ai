# Third-party browser assets

Scoped packaging check, **10 September 2026**. The production browser output
contained font binaries and minified JavaScript but no standalone notices
asset. The inspected MIT license bodies were absent from the minified JS.
This check did not inspect license metadata embedded inside font binaries.

The [third-party notices](../../apps/web/public/third-party-notices.txt) now
retain the installed packages’ copyright and license text. Vite copies this
file to `dist/third-party-notices.txt`, available as `/third-party-notices.txt`
when that build is served. This change does not modify an existing image or
release tag; publication of the rebuilt artifact requires a subsequent release.

## Inspected contents

A production Rollup module inspection found rendered code from React 19.2.8,
React DOM 19.2.8, Scheduler 0.27.0 and React Router 7.18.3. The
`react-router-dom` 7.18.3 browser entry re-exports router code and has the
same license; it is included under the shared router notice. The output also
contains Vite’s modulepreload polyfill and a Rollup CommonJS helper. Their
MIT texts come from Vite 7.3.6’s installed license file; the bundled CommonJS
helper’s standalone exact package version is not exposed by that artifact.

The 13 emitted WOFF/WOFF2 assets match their installed source bytes: three
Space Grotesk variable fonts and ten IBM Plex Mono regular fonts, from
`@fontsource-variable/space-grotesk` and `@fontsource/ibm-plex-mono` 5.3.0.
Both installed font licenses are SIL OFL 1.1. Their complete copyright
statements and license bodies are retained without rewriting.

## License provenance

The following paths are relative to the inspected installed workspace, not
public repository links. Versions come from those package manifests, rather
than the semver ranges in the app manifest. SHA256 values cover complete
source license files. Identical React-family and router license files are
included once under their shared package headings.

| Package | Installed version | License | Source SHA256 |
| --- | --- | --- | --- |
| `@fontsource-variable/space-grotesk` | 5.3.0 | OFL-1.1 | `18a4de52385f6b988782639d5d0cc1326e5a8c2de9a7f01d7b20d9aedcc60943` |
| `@fontsource/ibm-plex-mono` | 5.3.0 | OFL-1.1 | `23b0a9d0c6d3f140a0b77e483c5cfa6bba574325ef5cb189ed9f2fec4884533f` |
| `react` | 19.2.8 | MIT | `da6d3703ed11cbe42bd212c725957c98da23cbff1998c05fa4b3d976d1a58e93` |
| `react-dom` | 19.2.8 | MIT | `da6d3703ed11cbe42bd212c725957c98da23cbff1998c05fa4b3d976d1a58e93` |
| `scheduler` | 0.27.0 | MIT | `da6d3703ed11cbe42bd212c725957c98da23cbff1998c05fa4b3d976d1a58e93` |
| `react-router` | 7.18.3 | MIT | `77c9ee6a9c5d5782fb0c50b50d101189116314c14f7df0a1b0d385fc96a7ba49` |
| `react-router-dom` | 7.18.3 | MIT | `77c9ee6a9c5d5782fb0c50b50d101189116314c14f7df0a1b0d385fc96a7ba49` |
| `vite` | 7.3.6 | MIT | `a77a1c089806b39ad339535bdf3677f636c91d96693e8ad7b11fe733f650ea64` |
| `@rollup/plugin-commonjs runtime helper` | bundled in vite 7.3.6; standalone exact version not exposed | MIT | `a77a1c089806b39ad339535bdf3677f636c91d96693e8ad7b11fe733f650ea64` |

Exact installed source paths:

```text
node_modules/.pnpm/@fontsource-variable+space-grotesk@5.3.0/node_modules/@fontsource-variable/space-grotesk/LICENSE
node_modules/.pnpm/@fontsource+ibm-plex-mono@5.3.0/node_modules/@fontsource/ibm-plex-mono/LICENSE
node_modules/.pnpm/react@19.2.8/node_modules/react/LICENSE
node_modules/.pnpm/react-dom@19.2.8_react@19.2.8/node_modules/react-dom/LICENSE
node_modules/.pnpm/scheduler@0.27.0/node_modules/scheduler/LICENSE
node_modules/.pnpm/react-router@7.18.3_react-dom@19.2.8_react@19.2.8__react@19.2.8/node_modules/react-router/LICENSE.md
node_modules/.pnpm/react-router-dom@7.18.3_react-dom@19.2.8_react@19.2.8__react@19.2.8/node_modules/react-router-dom/LICENSE.md
node_modules/.pnpm/vite@7.3.6_@types+node@24.13.3/node_modules/vite/LICENSE.md
```

For Vite, only the complete core MIT section is copied. For the emitted
CommonJS helper, the complete MIT block under the shared Rollup plugins
heading is copied with Markdown `> ` quotation prefixes removed; copyright
wording, conditions, disclaimer and line breaks are preserved. These two
included sections have SHA256 values
`444c5ec3bf7f798af5c5179d734673cbcb115b22b1ef48e6d85bc941ac8777a2`
and `7b8136f76c483d03597500bfa991aae9be68d4629e1121cbf9b93aa727efe305`.

## Verification

- `pnpm --dir apps/web build` passed with the existing dependency lockfile.
- Repository public file, authoritative build-cache public file and rebuilt
  dist file are byte-identical: **15,931 bytes**, SHA256
  `f16a58a2ec41fa80376e9bdd12bb9f74d548ded99412434bf7c257fd58b9e89b`.
- Every retained license body was compared with its installed source or the
  explicitly described source section; all 13 built fonts still match their
  original package binaries.
- Inspected `pnpm-lock.yaml` SHA256:
  `1f8ec37cb83dc23aa3f9c591135daec563d9928eab30da8a1b0c09f665afcaef`.
- The existing localhost production API served `/third-party-notices.txt`
  with HTTP 200, `text/plain; charset=utf-8` and `Cache-Control: no-cache`.
  The downloaded 15,931 bytes match the repository notice hash above. This
  read created no run and called no provider. It does not establish that the
  earlier `63cf7fd` image contains this later asset.

This is a browser-artifact notice check, not an audit of every container OS
package, Python dependency, external documentation quotation or submission
media right. It makes no general legal-clearance claim. No source behavior,
font binary, UI design, release tag or published image was changed here.
