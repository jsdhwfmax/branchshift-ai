# Fixed first-run evidence

These files are byte-for-byte extracts from public GitHub Actions run 38331091063.

Upstream: https://github.com/NowanIlfideme/pydantic-yaml/tree/54ff4bad7bca758a9dd22a791b707a2b9c27159e

`baseline/repository-evidence.json` contains upstream source under the accompanying MIT license, `upstream-LICENSE`. No source is executed during local preparation. Baseline outcome: 14 passed, 1 original xfail; the original no-assertion `test_basic.py::test_readme` is retained. Candidate checks must preserve the entire original suite, test identities, configuration and previous passing outcomes.

`candidate-environment/constraints.txt` contains the complete resolved v2 runtime from that comparison. Its exact bytes are enforced by the candidate harness; this is version locking, not a universal dependency security claim.

This evaluation runs on GitHub-hosted Linux, not a Nebius Sandbox. No image UUID or checkpoint is fabricated.
