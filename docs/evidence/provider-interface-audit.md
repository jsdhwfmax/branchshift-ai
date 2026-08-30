# Provider interface audit — 31 August 2026

## Sources checked

- [Nebius Token Factory quickstart](https://docs.tokenfactory.nebius.com/quickstart)
- [Structured output and JSON](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
- [Contree SDK getting started](https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/getting-started)
- [Contree branching workflows](https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/branching)
- [Official Contree SDK repository](https://github.com/nebius/contree-sdk)

## Confirmed contract

- Inference uses `https://api.tokenfactory.nebius.com/v1/` through the
  OpenAI-compatible chat-completions API.
- Structured output accepts `response_format.type=json_schema`; BranchShift
  validates returned JSON through Pydantic before accepting a plan.
- A persisted Contree image state has a stable UUID. Executing different
  commands from the same state produces independent child states.
- BranchShift uses `disposable=False` for states that must remain branchable
  and bounds captured output with `truncate_output_at`.

## SDK packaging gap found

The current documentation and the `main` branch construct a
`contree_client.httpx.ContreeAsyncClient` and pass it to `Contree`. The newest
installable PyPI artifact discovered during setup, `contree-sdk==0.4.0.dev5`,
still exposes the older `Contree(token=..., base_url=...)` constructor
internally. The provider adapter detects the installed surface and supports
both forms. A credentialed Sandbox branching spike remains mandatory before
live mode is enabled.

