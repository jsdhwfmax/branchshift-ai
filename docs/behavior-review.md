# Review behavior beyond the existing tests

Dependency upgrades can pass a project's tests while changing untested inputs.
BranchShift accepts explicit examples to make selected differences reviewable.
The examples do not replace the original tests or choose the winning patch.

For the authored example project, save this JSON to a local file:

```json
{
  "cases": [
    {
      "id": "ordinary-name",
      "module": "sample_app.models",
      "model": "User",
      "payload": {"id": 1, "name": "Ada", "email": "ada@example.com", "created_at": "2026-01-01T00:00:00"}
    },
    {
      "id": "numeric-name",
      "module": "sample_app.models",
      "model": "User",
      "payload": {"id": 1, "name": 123, "email": "ada@example.com", "created_at": "2026-01-01T00:00:00"}
    }
  ]
}
```

Provide it in the live form's optional behavior-review field, or pass
`--behavior-probes /absolute/path/examples.json` to `app.cli.live_run`.
The API's `behavior_probes` field accepts the same object. These operations
start live provider work and use the configured account's credits.
Use fixed values for time or random defaults when possible. Otherwise differences
may reflect nondeterminism, and still require human interpretation.

## What is compared

The server freezes the same declarations for the original checkpoint, each
returned candidate checkpoint, and the clean revalidation checkpoint. It imports
the specified installed module and BaseModel class in Sandbox, constructs the
model with the JSON payload, and obtains its JSON representation with aliases.
Model imports and validators never run in the API process.

Each example records one of:

- **Accepted:** the normalized JSON value, retaining JSON types.
- **Rejected:** the exception class only. Exception messages are not compared.
- **Unsupported:** the model could not be imported, it was not a supported
  Pydantic model, serialization failed, or output exceeded the bound.

Comparison reports **match**, **different**, or **unsupported**. A difference in
acceptance, JSON output or exception class needs maintainer review. It can be
an intended breaking change; the application does not silently declare it a
bug or hide the otherwise passing original tests. Missing results and timeouts
remain unknown, rather than matching by default.

## Boundaries

There are at most 12 examples and 16 KiB of declarations. The HTTP request body
has a separate 8 KiB default limit; CLI input still has the declaration limit.
Each returned JSON value is at most 4 KiB, with a 16,000-byte total result bound.
Each probe execution has a 30-second Sandbox timeout. Inputs are data, not
scripts; there is no arbitrary expression or method-name option.

These examples do not measure all inputs, side effects, performance, full
exception messages, schema generation or complete application equivalence.
Even an accepted model may perform project-defined side effects inside its
isolated probe child. Probe children never replace the original baseline or
the checkpoint whose tests are recorded.

The JSON export preserves the full declared examples, observations and review
results. Markdown and the interface show concise comparisons. Historical runs
without examples remain labeled as having no behavior review.
