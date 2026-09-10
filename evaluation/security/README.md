# Controlled boundary fixtures

These six `.py.txt` files are test data. **Do not import or execute them on the
host.** Local tests parse their syntax and inspect their structure. Only the
reviewed remote probe driver constructs executable command strings, and it
sends those strings to the Sandbox adapter.

The prompt-injection fixture is not remotely executed. Local application tests
simulate a hostile model that obeys the comment and attempts to change a
protected or unknown file. They exercise the actual editor validation and
confirm that the attempt fails before Sandbox execution. They do not measure
the probability of a real model following an injection.

The other five fixtures have deliberately narrow effects:

| Case | Controlled action | Interpretation |
| --- | --- | --- |
| Secret discovery | Read one synthetic remote file; check presence of one freshly generated fake host environment variable | Tests only that canary boundary; no real credentials are inspected or returned |
| Network access | One HTTPS `HEAD /` to `example.com`, two-second socket timeout, no body, credentials, redirects or retries | Success means public egress is allowed; an error does not prove an egress deny policy |
| Host path | Try to read the exact fresh `/tmp/branchshift-security-*/host-only-canary.txt` created by the driver | No host directory enumeration, configuration access or mounts; tests only this fake file |
| Infinite output | Rate-limited output loop, about 200 KiB/s, with an independent eight-second alarm | Observe captured bytes; truncating a response does not cap the producer's total output |
| Long running | One `sleep(60)` under the same eight-second alarm | No busy loop, forks or child processes; distinguish the probe's alarm from provider enforcement |

The remote wrapper checks a marker made in its prepared Sandbox state before
starting the fixture, then installs its alarm. The host canary value is never
included in a remote command or report. The driver restores the prior value of
its dedicated fake environment variable and deletes only its own temporary
directory afterward.

Inspect without credentials, providers or fixture execution:

```sh
PYTHONPATH=services/api python -m app.cli.security_probes
```

After authorization for the small real-provider experiment, the driver can be
run with an unused private output path:

```sh
PYTHONPATH=services/api python -m app.cli.security_probes \
  --execute --output /absolute/private-evidence/security-probes.json
```

The driver issues one baseline-adapter call and five sequential `run` calls,
each with a requested three-second provider execution timeout; it makes no
model calls. SDK HTTP requests and billable operations may differ from those
adapter counts. The wrapper's eight-second alarm is a separate experimental
safeguard. Client waits are bounded at 45 seconds for preparation and 20 seconds
per probe; a client timeout is not proof of remote process termination.

Outputs contain fixture/driver/adapter source hashes, the actual installed
`contree-sdk` distribution version, actual returned IDs, exits, byte counts,
timings and a restricted set of observed facts. Arbitrary stdout, stderr and
exception messages are not persisted. Missing or malformed observations remain
missing. Successful JSON export does not mean every isolation property passed.
Existing evidence files are never overwritten. These observations are separate
from the migration-success manifest in `evaluation/attempts.json`.

The SDK's `truncate_output_at` setting is expressed in bytes. This driver
measures UTF-8 bytes of the text returned by the adapter after redaction; it
does not infer byte lengths from Python string length. The output-loop fixture
uses ASCII, so its byte and character counts coincide. The adapter source
hash and installed SDK version identify the implementation used for a report;
neither is derived from environment credentials.

Current local checks and remaining live evidence are documented in
[security boundaries](../../docs/evidence/security-boundaries.md).
