# Token Factory Sandbox branching spike

Status: **real three-branch Sandbox spike passed on 10 September 2026**.
The Beta welcome email and a credentialed execution now confirm access.
SDK: `contree-sdk==0.4.0.dev5`; image: configured `CONTREE_IMAGE`.
Total elapsed: **4.581 seconds**.

| State | Checkpoint UUID | Observed marker |
|---|---|---|
| Baseline | `83134b3c-c6d2-49cd-84f8-2bd0b3e2831c` | Baseline setup wrote `baseline` |
| Minimal | `d059aa4a-da09-44d6-8f4d-c10b2bce6225` | `baseline\nminimal` |
| Compatibility | `190878b6-6e0a-424f-8793-bfa6eb8b5263` | `baseline\ncompatibility` |
| Refactor | `b39e0432-6687-440d-822a-d66ba61d4d66` | `baseline\nrefactor` |

Each child started from the identical baseline UUID. Three distinct UUIDs and
the expected per-branch output were asserted by `app.cli.sandbox_spike`.
Per-branch elapsed: 1.310s, 2.156s, 2.166s. This proves Sandbox branching;
it does not yet prove an end-to-end migration or a public deployment.

The original Documents `.venv` blocked reading SDK metadata; the successful
run used a fresh local cached Python 3.13 environment with the declared project
dependencies. No credential values were included in the output.

## Earlier attempt (31 August 2026)

The credentialed Sandbox spike reached the public service, but `whoami`
reported `spawn=false`, `spawn_disposable=false`, and `list=false`; the first
spawn therefore failed closed with HTTP 403. Token Factory's Sandbox page
requires a separate beta-access request for the project.

The IAM adapter sends both the API key and required project ID. The Beta access
form was submitted successfully on 31 August; the earlier 403 is now resolved.

Expected command:

```bash
BRANCHSHIFT_MODE=live NEBIUS_API_KEY=... \
  .venv/bin/python -m app.cli.sandbox_spike
```

Evidence to record after the run: redacted operation IDs, baseline UUID, three
child UUIDs, per-branch marker contents, elapsed seconds, and SDK version.
