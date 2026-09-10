# Provider interface audit — updated 10 September 2026

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

The documentation examples reviewed on 31 August construct a
`contree_client.httpx.ContreeAsyncClient` and pass it to `Contree`. The newest
installable PyPI artifact discovered during setup, `contree-sdk==0.4.0.dev5`,
uses `Contree(ContreeConfig(auth=IAMAuth(token=..., project_id=...)))` in the
verified installed environment. The adapter is pinned to that explicit surface;
it does not claim support for untested alternate constructors.

The credentialed branching spike passed on 10 September (see
[Sandbox evidence](sandbox-spike.md)). Real baseline preparation also cloned
the public repository and passed all 13 fixture tests in a Sandbox. The first
full migration attempt then failed closed when Nemotron omitted target file
names. These are separate evidence gates; Sandbox availability alone is not
proof that a generated migration works.
