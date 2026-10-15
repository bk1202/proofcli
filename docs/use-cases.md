# Practical use cases

ProofCLI is useful when a command's promised result can be expressed as repeatable output assertions. Keep the spec beside a small representative fixture, run it in CI, and retain evidence for failures.

## Catch an exporter that silently drops rows

The [CSV export example](../examples/export/good.json) reads a known three-row fixture, writes a JSON summary, and writes a normalized CSV:

```console
proofcli validate examples/export/good.json
proofcli run examples/export/good.json --artifacts export-evidence --report export-report.json
```

The contract requires the JSON summary to contain a row count of 3 and a total of `"33.75"`, the currency to be `"CAD"`, and the CSV to contain the required columns and at least three data rows. Input staging means an old output in the caller's directory cannot satisfy those checks.

Run the intentional regression with a different evidence directory:

```console
proofcli run examples/export/false-success.json --artifacts broken-evidence --report broken-report.json
```

The exporter still exits 0 and prints success. Both files exist, are nonempty, and parse. Its JSON contains zero records and its CSV has only a header. Content assertions fail, ProofCLI exits 1, and both incorrect files remain available in `broken-evidence`.

These assertions suit this fixture. A minimum row count alone would allow duplicated records, and a summary field alone would allow a lying summary. If those failures matter, add exact expected JSON data for a small fixture or have the command emit a stronger independently checkable result. Do not mistake a weak contract for proof of the whole transformation.

## Gate generated artifacts in CI

After installing ProofCLI in CI, run the same command you use locally:

```console
proofcli run path/to/export-contract.json --report acceptance-report.json
```

Let ProofCLI's exit code gate the job. Save `acceptance-report.json` with your CI system's artifact mechanism. Add `--artifacts` when you also want declared outputs preserved; the destination must not already exist. ProofCLI writes local evidence, and the CI system controls uploading and retention.

A useful spec tests a small, stable input whose expected result you know. It should exercise the real executable, dependencies, and file formats. Replacing the exporter with a mock only proves that the mock obeys the spec.

## Check an agent's file-producing command

An agent can call `proofcli run SPEC --json` and inspect the report rather than treating an exit code or success message as sufficient evidence. The command, fixture, and assertions remain reviewable JSON.

Choose assertions around the promised artifact: required text in a generated configuration, expected nested fields in a JSON manifest, or required CSV headers and row counts. Keep the contract independently defined when possible. An agent writing both an incorrect artifact and matching incorrect expectations can make a pass meaningless.

ProofCLI does not judge prose quality, visual correctness, audio duration, or whether a business decision is sound. It runs trusted programs with your permissions, not in a security sandbox.
