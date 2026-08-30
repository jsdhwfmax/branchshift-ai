# BranchShift UI direction

## Product subject and single job

The interface is a migration control room for maintainers. Its single job is
to let a judge understand why three branches began from the same baseline and
why one patch won.

## Pass one: visual system and wireframe

Token system: Chalk `#F4F6F2`, Graphite `#17201E`, Blueprint `#2457F5`, Signal
`#F2B544`, Pass `#0B8A6A`, Fault `#D95C59`. Space Grotesk carries product and
body language; IBM Plex Mono carries code, metrics, and state.

Desktop wireframe:

```text
[wordmark] [mode] [integration health]
[repo input________________] [launch]
[baseline node]---+---[minimal lane]-------+
                  +---[compatibility lane]-+--> [winner gate]
                  +---[refactor lane]------+        |
[event ledger] [evidence comparison]        [patch]
```

Mobile stacks the control strip, baseline, lanes, evidence, and patch in that
order. The signature element is the branch rail: three color-coded paths split
from one checkpoint and mechanically converge on the evidence-selected winner.

## Pass two: critique and revision

The first sketch risked becoming a generic SaaS landing page with a large hero,
soft gradient, and repeated rounded cards. The revision removes the hero,
starts with the actual repository control strip, uses squared instrument panels,
and spends visual emphasis only on the branch rail and winner gate. Motion is
brief, transform/opacity-only, and disabled by `prefers-reduced-motion`.

