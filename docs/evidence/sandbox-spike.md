# Token Factory Sandbox branching spike

Status: **waiting for the emailed hackathon promo code and a Nebius API key
with Sandbox access**. The official credit form was submitted successfully on
31 August 2026; no billing or card data was entered.

The offline adapter and SDK import path are verified. The credentialed exit
condition is intentionally not marked complete until one baseline state forks
into three child UUIDs and each child can read only its own marker.

Expected command:

```bash
BRANCHSHIFT_MODE=live NEBIUS_API_KEY=... \
  .venv/bin/python -m app.cli.sandbox_spike
```

Evidence to record after the run: redacted operation IDs, baseline UUID, three
child UUIDs, per-branch marker contents, elapsed seconds, and SDK version.
