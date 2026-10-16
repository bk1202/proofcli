# GitHub Action

The repository root is a composite Action for GitHub-hosted Linux, Windows, and macOS runners. It sets up Python 3.13 and executes the ProofCLI code shipped at the selected Git ref. It does not install ProofCLI from a moving index version or change global Python packages.

```yaml
name: Verify exports
on: [push, pull_request]
permissions:
  contents: read
jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: bk1202/proofcli@v0.4.2
        id: proof
        with:
          spec: tests/export-contract.json
          report: proofcli-result.json
          artifacts: proofcli-evidence
      - uses: actions/upload-artifact@v6
        if: always()
        with:
          name: proofcli-evidence
          path: |
            proofcli-result.json
            proofcli-evidence/
```

Pin actions to full commit IDs when required by your dependency policy. The Action itself pins its Python setup dependency. Read-only repository permissions suffice; the commands in your contract may need other application-specific access.

`spec` is required. Paths are relative to the current workspace. `report` defaults to a new runner temporary directory; `artifacts` is optional and must name a directory that does not exist. The default report is available at `steps.proof.outputs.report`. Output files are not automatically uploaded.

The Action returns ProofCLI's exit code. `status` and `exit-code` describe that execution, not an existing report left at a failed destination. If you set `continue-on-error: true`, you are choosing to tolerate a failed contract; check `steps.proof.outcome` and the outputs explicitly. An invalid contract returns `2`; a wrong export returns `1` even when its command exited `0`.

Arguments are passed through environment variables and Python argv, not interpolated into shell commands. This does not make a contract safe to execute: contracts can run arbitrary commands with runner permissions. Do not execute untrusted pull-request contracts with `pull_request_target` or repository secrets. `{python}` refers to the Action's Python interpreter; install any dependencies required by your command into that environment, or provide an explicit executable path.

Self-hosted runners additionally need GitHub's supported Node runtime, Bash, and the setup-python prerequisites. Only GitHub-hosted runners are covered by the integration matrix.
