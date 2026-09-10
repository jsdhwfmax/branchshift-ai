# Repository tracked-checkout size acceptance gate

The live baseline setup checks the cloned repository before creating the
project virtual environment or installing its dependencies. Configure
`MAX_REPOSITORY_BYTES` as a positive integer number of bytes; its default is
52,428,800 bytes (50 MiB). Invalid, zero or negative environment values fail
startup rather than silently disabling the gate. The configured value is part
of `runtime_config_digest`.

## What is measured

A trusted Python script executes inside the Sandbox with Python isolated mode
(`-I`). It asks Git for NUL-delimited index entries at `/workspace/repo`, then
uses `lstat` to sum the lengths of tracked regular files and symbolic links.
Symbolic-link targets are not followed: a dangling link is measured by the
link's own length. Gitlinks/submodules, mismatched file types, missing tracked
files, malformed entries and Git/filesystem errors reject the checkout.

The scan covers the entire cloned repository, including files outside a
selected `project_path`. A total equal to the configured limit is accepted;
the scan fails immediately when its observed sum becomes greater. Acceptance
prints the observed total and configured limit as setup-output markers.
Rejection reports the configured limit and the subtotal already observed;
that subtotal is not presented as a completed scan of the repository.

This gate never imports or executes repository Python modules. Only the
accepted setup continues to the existing dependency-installation and baseline
test stages inside the Sandbox.

## Boundaries

This is a **post-checkout, pre-install acceptance gate**. It does not measure
or enforce a compressed archive/download limit, `.git` object storage, peak
clone/checkout disk usage, untracked files, later installed dependencies,
generated output, or total Sandbox disk/CPU/memory/network consumption. The
shallow filtered clone remains an optimization, not a guaranteed transfer
cap. The application does not claim SDK controls that it does not expose.

The scan itself has no separate file-count or memory guarantee. Its remote
execution remains subject to the existing setup/run timeout and output
controls. The original plan's archive-size wording is therefore represented
by this narrower, explicit repository acceptance rule.

## Verification and provenance

Local tests run the trusted guard against newly created, controlled temporary
Git fixtures. They cover the equal/one-byte-over boundary, aggregate file
sizes, filenames containing tabs/newlines/shell syntax, regular and dangling
symlinks, missing or changed tracked files, Git errors and unsupported gitlinks.
A synthetic clone/virtual-environment/installer verifies that a large file
outside the selected project still rejects setup before either environment
creation or installation. No external repository code, dependency install or
live provider is used by these tests.

The settings tests reject invalid environment and constructor values. A
provenance test confirms that changing the limit changes the runtime
configuration digest while changing a credential does not. The RunManager
tests verify that the configured value reaches BaselineRunner.

The 15-case-slot live matrix at frozen commit
`92c733a1338cc7abdbcf04ca00be363158fd126c` predates this addition. Its original
summaries and provenance are unchanged; it is not evidence that this gate ran
in those historical cases. A later deployed release needs its own release
verification.
