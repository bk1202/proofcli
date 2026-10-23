# Using ProofCLI with AI coding agents

An agent can run a command, see exit code 0, and report the change as done while an output file is wrong. Keep a JSON contract for the output the change should produce. Have the agent run that contract before it claims the work is done. Use the same file in CI.

The commands below are from a checkout of this repository, using the example exporter. In another project, point them at that project's contract.

## Before calling the work done

This contract is supposed to fail. ProofCLI exits 1. The exporter exits 0 and writes `999.00` where the contract expects `8.25`:

```console
proofcli run examples/export/wrong-value.json
```

A contract that matches the exporter exits 0:

```console
proofcli run examples/export/good.json
```

`validate` checks the contract and does not run the command:

```console
proofcli validate examples/export/good.json
```

`--json` prints one JSON object on stdout. `--report` writes that report to a file. `--artifacts` copies the declared output files into a directory that must not already exist:

```console
proofcli run examples/export/good.json --json
proofcli run examples/export/wrong-value.json --report proofcli-report.json --artifacts proofcli-output
```

If ProofCLI exits 1, the report names the failed check, the path, the expected value, and the actual value. Exit code 0 means every check in that contract passed. It does not mean the rest of the diff is correct.

## On pull requests

The [GitHub Action](github-action.md) checks out nothing by itself. After `actions/checkout`, it runs the ProofCLI source from the selected ref and fails the step when verification fails:

```yaml
steps:
  - uses: actions/checkout@v7
  - uses: bk1202/proofcli@v0.4.2
    with:
      spec: examples/export/good.json
```

Change `spec` to the contract that should pass for the pull request. The Action exposes `report`, `status`, and `exit-code` outputs. Optional `report` and `artifacts` inputs choose where evidence is saved. Pin a full commit SHA instead of `@v0.4.2` when the workflow needs an immutable action.

## Limits

A pass covers the checks in the contract and the files that run produced. If the agent edits the contract so a bad file matches, the check can pass. Review contract changes the same way you review the code.

ProofCLI is not a sandbox. The command runs with the permissions of whoever starts it. It does not judge prose, visual layout, or whether a business decision is right. Those limits are also listed in the [README](../README.md#limitations).
