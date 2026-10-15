# ProofCLI

**Check the files a command actually produced, beyond exit code 0.**

ProofCLI runs a trusted command in a fresh directory, stages declared fixtures, checks its logs and output contents, and returns an exit code plus a human or JSON report. Use it for small acceptance contracts around exporters, generators, data transforms, and agent workflows.

Python 3.10+ · Windows 10/11 and macOS · MIT · **No runtime dependencies**

## Install

Use a virtual environment with an existing Python installation. Releases contain a universal wheel, source distribution, and SHA-256 checksums. This is not a standalone executable.

Windows (PowerShell):

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install https://github.com/bk1202/proofcli/releases/download/v0.3.0/proofcli-0.3.0-py3-none-any.whl
.venv\Scripts\proofcli --help
```

macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install https://github.com/bk1202/proofcli/releases/download/v0.3.0/proofcli-0.3.0-py3-none-any.whl
.venv/bin/proofcli --help
```

Use the environment's `python -m proofcli` if the console command is not on PATH. From a checkout, use `python -m pip install .`. A versioned Git installation is also available: `python -m pip install git+https://github.com/bk1202/proofcli.git@v0.3.0` (requires Git). This project is not published to PyPI.

## First contract

The examples below assume the environment's executables are on PATH; otherwise use their full paths as above.

```console
proofcli init proofcli.json
proofcli validate proofcli.json
proofcli run proofcli.json --report verification.json --artifacts evidence
```

`init` writes a working example without executing it. `validate` checks the schema, not dependency availability. `run` executes and verifies. The legacy `proofcli SPEC` form still works.

Artifact directories must be new. Reports are replaced atomically when explicitly reused; the spec, input sources, and retained output paths are protected. Failed files are preserved with `--artifacts`. `--json` emits one JSON object on stdout; child logs stay inside its fields.

## A failure exit codes miss

Clone this repository to try the [real CSV exporter](examples/export/export.py). After installation:

```console
proofcli run examples/export/good.json
proofcli run examples/export/wrong-value.json --report bad-report.json --artifacts bad-output
```

Both exporter commands exit 0 and create valid, nonempty JSON and CSV. The second silently changes Grace's amount to `999.00` while keeping the original total. Its old success message, row-count check, and JSON summary check still pass. Exact record assertions fail and ProofCLI returns 1. Diagnostics identify `$/rows/1/amount`, with expected and actual values.

Other runnable regressions cover [missing records with a lying summary](examples/export/missing-record.json), [unexpected CSV columns](examples/export/extra-column.json), and [no records](examples/export/false-success.json). These use the real exporter and fixture, not mocked subprocesses.

## Contract shape

```json
{
  "version": 1,
  "argv": ["{python}", "{spec_dir}/export.py", "input.csv", "report.json"],
  "inputs": [{"source": "fixtures/input.csv", "dest": "input.csv"}],
  "timeout_seconds": 10,
  "verification_timeout_seconds": 5,
  "expect": {
    "exit_code": 0,
    "files": [{
      "path": "report.csv",
      "csv": {
        "columns": ["id", "customer", "amount"],
        "exact_columns": true,
        "rows": [
          {"id": "1", "customer": "Ada", "amount": "12.50"},
          {"id": "2", "customer": "Grace", "amount": "8.25"},
          {"id": "3", "customer": "Linus", "amount": "13.00"}
        ]
      }
    }]
  }
}
```

Assertions include expected exit code, stdout/stderr regex, regular file existence/minimum size, file-text regex, JSON object subsets (`json_contains`), exact JSON values (`json_equals`), and CSV headers/counts/exact ordered records. CSV values are strings. JSON booleans do not equal numbers; output decimals are compared without binary float rounding.

`argv` has **no implicit shell**, variable expansion, pipes, or globbing. `{python}` selects ProofCLI's interpreter, preserving its virtual environment. `{spec_dir}` and `{work_dir}` expand inside arguments. Windows batch files are rejected; invoke an interpreter explicitly when shell behavior is intentional.

See the [complete specification](docs/specification.md), [report format](docs/reports.md), and [use cases](docs/use-cases.md).

## Exit codes and CI

| Exit | Meaning |
| --- | --- |
| `0` | Every requested assertion completed and passed, or `init`/`validate` succeeded. |
| `1` | Command/expectation failure, timeout, output overflow, or assertion deadline exceeded. |
| `2` | Invalid usage/spec, supervision, file handling, or report I/O error. |
| `130` | Ctrl+C/SIGINT or Windows Ctrl+Break. |
| `143` | SIGTERM interruption. |

The child's actual exit code is separate; on POSIX a negative code indicates a signal. Check `status` and `verification_complete` before treating a report as evidence. Use your CI system's artifact mechanism to upload retained files/reports.

## Guarantees and limits

- Fresh directories prevent previous-run output from satisfying checks. Inputs are independent copies with byte counts/SHA-256 fingerprints. Output links/reparse points and hard-link aliases of staged inputs are rejected.
- Each stream is bounded to 1 MiB in memory; overflow stops the command. Logs are not first written to unbounded temporary files. Specs and semantic file reads are also capped at 1 MiB.
- Assertions run in a separate supervised process with an independent deadline. A pathological regex cannot indefinitely block the CLI.
- Ordinary descendants are terminated on completion, timeout, and handled interruption: Job Objects on Windows, process groups on macOS. POSIX children that detach into another session can escape. SIGKILL, crashes, native uninterruptible I/O, and external filesystem races are not universally controllable.
- **This is not a security sandbox.** Commands inherit your environment and user permissions. They can access other files/network, modify external state, and create arbitrarily large output files. There are no general CPU, memory, network, or disk quotas. Reports may contain sensitive argv and logs.
- A pass proves only the declared properties of observed files and decoded logs. Weak assertions, unrepresentative fixtures, or an agent changing both code and expectations can still give false confidence. No visual, audio, business, or universal semantic correctness is established.

See the [adversarial audit and unresolved limits](docs/audit-0.3.md). This project has not had an independent third-party security review; green CI is not a blanket production-readiness claim.

## Why not pytest or a shell script?

| Tool | Good fit | Tradeoff |
| --- | --- | --- |
| ProofCLI | Small, reviewable JSON contracts around real commands; consistent reports across Windows/macOS. | Limited assertion vocabulary and fixed resource policies. |
| pytest | Arbitrary Python assertions, rich fixtures, parametrization, plugins, and complex application tests. | Python test code and a pytest dependency; subprocess ownership/reporting must be chosen or implemented. |
| Shell scripts | Short checks with existing utilities and direct composition. | Quoting, utilities, cleanup, and reports vary across shells/platforms. |

ProofCLI complements general testing tools. Use pytest when verification logic is complex; invoke ProofCLI from pytest, shell, or CI when a declarative contract is useful. No speed or reliability advantage over those tools is claimed.

## Develop and release

```console
python -m pip install --require-hashes -r requirements-build.txt
python -m build --no-isolation
python tools/verify_dist.py
python -m pip install .
python -m unittest discover -s tests -v
```

CI exercises the installed wheel and fresh wheel/sdist installations on Windows/macOS. Build tools are hash-locked; Actions are pinned to commit IDs. [Release instructions](docs/releasing.md) describe validation, checksums, and assets.

See [CHANGELOG](CHANGELOG.md), [SECURITY](SECURITY.md), and [CONTRIBUTING](CONTRIBUTING.md). Licensed under [MIT](LICENSE).

Motivation included CLI-Anything issues [#406](https://github.com/HKUDS/CLI-Anything/issues/406) and [#407](https://github.com/HKUDS/CLI-Anything/issues/407). ProofCLI is independently implemented; no CLI-Anything code was copied.
